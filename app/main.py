import asyncio
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager, nullcontext
from pathlib import Path
from threading import Lock
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.core.config import Settings
from app.core.database import database
from app.models import Base
from app.api.routes import router
from app.services.risk import RiskEngine
from app.services.adapters import LLMScamClassifier, OpenWorkerScamClassifier, OpenWorkerRouterClient
from app.services.notifications import deliver, InAppNotificationProvider

logger = logging.getLogger('yatharth')

def create_app(settings=None, classifier=None):
    settings = settings or Settings()
    engine, sessions = database(settings.database_url)
    async def delivery_loop():
        while True:
            try:
                await asyncio.to_thread(deliver, sessions, InAppNotificationProvider())
            except SQLAlchemyError:
                logger.warning('{"event":"notification_database_unavailable"}')
            await asyncio.sleep(5)
    @asynccontextmanager
    async def lifespan(app):
        try:
            Base.metadata.create_all(engine)
        except SQLAlchemyError:
            logger.warning('{"event":"database_startup_unavailable"}')
        task = asyncio.create_task(delivery_loop())
        yield
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass
        engine.dispose()
    app = FastAPI(title='Yatharth — Digital Safety', version='0.1.0', lifespan=lifespan, description='Protection, not surveillance. Internal prototype; not an emergency-response system. Scores are not probabilities. Register, login, then use Authorize with the bearer token.')
    app.state.settings, app.state.engine, app.state.sessions = settings, engine, sessions
    app.state.db_lock = Lock() if settings.database_url.startswith('sqlite') else nullcontext()
    if classifier is None:
        if settings.llm_enabled and settings.llm_key and settings.llm_url and settings.llm_model:
            classifier = LLMScamClassifier(settings.llm_url, settings.llm_key, settings.llm_model)
        elif settings.openworker_enabled:
            classifier = OpenWorkerScamClassifier(OpenWorkerRouterClient(), settings.llm_model)
    app.state.risk_engine = RiskEngine(settings, classifier)
    if settings.cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False, allow_methods=['GET','POST'], allow_headers=['Authorization','Content-Type'])
    buckets = defaultdict(deque)
    @app.middleware('http')
    async def guard(request: Request, call_next):
        # Small single-process MVP limiter; replace at the gateway before scaling.
        if request.method == 'POST':
            key = request.client.host if request.client else 'local'
            bucket = buckets[key]; clock = time.monotonic()
            while bucket and bucket[0] < clock-60: bucket.popleft()
            if len(bucket) >= 60: return JSONResponse({'detail':'Too many requests'}, status_code=429, headers={'Retry-After':'60'})
            bucket.append(clock)
            chunks = []; size = 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > 65536: return JSONResponse({'detail':'Request too large'}, status_code=413)
                chunks.append(chunk)
            request._body = b''.join(chunks)
        response = await call_next(request)
        response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','X-Frame-Options':'DENY'})
        if request.url.path == '/':
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'"
        return response
    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        return JSONResponse({'detail':[{'loc':e['loc'],'msg':e['msg'],'type':e['type']} for e in exc.errors()]}, status_code=422)
    @app.exception_handler(IntegrityError)
    async def conflict(request, exc):
        return JSONResponse({'detail':'Conflicting record; retry with unique input'}, status_code=409)
    @app.exception_handler(SQLAlchemyError)
    async def db_error(request, exc):
        logger.warning('{"event":"database_request_failed"}')
        return JSONResponse({'detail':'Storage unavailable; no successful analysis is claimed. Retry later.'}, status_code=503)
    app.include_router(router)
    frontend = Path(__file__).resolve().parent.parent / 'frontend'
    if frontend.exists():
        app.mount('/static', StaticFiles(directory=frontend), name='static')
        @app.get('/', include_in_schema=False)
        def dashboard(): return FileResponse(frontend / 'index.html')
    return app

app = create_app()
