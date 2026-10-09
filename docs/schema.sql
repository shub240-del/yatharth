
CREATE TABLE users (
	name VARCHAR(100) NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	phone VARCHAR(30), 
	role VARCHAR(30) NOT NULL, 
	password_hash TEXT NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
)

;



CREATE TABLE families (
	name VARCHAR(100) NOT NULL, 
	owner_id VARCHAR(36) NOT NULL, 
	join_digest VARCHAR(64) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(owner_id) REFERENCES users (id)
)

;



CREATE TABLE audit_logs (
	family_id VARCHAR(36), 
	actor VARCHAR(36) NOT NULL, 
	action VARCHAR(50) NOT NULL, 
	resource VARCHAR(100) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(family_id) REFERENCES families (id)
)

;
CREATE INDEX ix_audit_logs_family_id ON audit_logs (family_id);


CREATE TABLE consents (
	family_id VARCHAR(36) NOT NULL, 
	protected_person_id VARCHAR(36) NOT NULL, 
	scope VARCHAR(40) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	external_ai_allowed BOOLEAN NOT NULL, 
	granted_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (family_id, protected_person_id, scope), 
	FOREIGN KEY(family_id) REFERENCES families (id), 
	FOREIGN KEY(protected_person_id) REFERENCES users (id)
)

;
CREATE INDEX ix_consents_family_id ON consents (family_id);


CREATE TABLE events (
	family_id VARCHAR(36) NOT NULL, 
	person_id VARCHAR(36) NOT NULL, 
	event_type VARCHAR(40) NOT NULL, 
	source VARCHAR(30) NOT NULL, 
	payload JSON NOT NULL, 
	timestamp TIMESTAMP WITH TIME ZONE NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(family_id) REFERENCES families (id), 
	FOREIGN KEY(person_id) REFERENCES users (id)
)

;
CREATE INDEX ix_events_family_id ON events (family_id);


CREATE TABLE family_members (
	family_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	relationship VARCHAR(60) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (family_id, user_id), 
	FOREIGN KEY(family_id) REFERENCES families (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;
CREATE INDEX ix_family_members_family_id ON family_members (family_id);


CREATE TABLE messages (
	family_id VARCHAR(36) NOT NULL, 
	sender_id VARCHAR(36) NOT NULL, 
	content TEXT, 
	source VARCHAR(30) NOT NULL, 
	timestamp TIMESTAMP WITH TIME ZONE NOT NULL, 
	request_id VARCHAR(100), 
	content_digest VARCHAR(64) NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (sender_id, request_id), 
	FOREIGN KEY(family_id) REFERENCES families (id), 
	FOREIGN KEY(sender_id) REFERENCES users (id)
)

;
CREATE INDEX ix_messages_family_id ON messages (family_id);


CREATE TABLE risk_events (
	family_id VARCHAR(36) NOT NULL, 
	message_id VARCHAR(36) NOT NULL, 
	risk_type VARCHAR(50) NOT NULL, 
	risk_score INTEGER NOT NULL, 
	severity VARCHAR(20) NOT NULL, 
	confidence FLOAT NOT NULL, 
	signals JSON NOT NULL, 
	explanation TEXT NOT NULL, 
	recommended_action TEXT NOT NULL, 
	model_version VARCHAR(100) NOT NULL, 
	decision_trace JSON NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(family_id) REFERENCES families (id), 
	UNIQUE (message_id), 
	FOREIGN KEY(message_id) REFERENCES messages (id)
)

;
CREATE INDEX ix_risk_events_family_id ON risk_events (family_id);


CREATE TABLE alerts (
	family_id VARCHAR(36) NOT NULL, 
	risk_event_id VARCHAR(36) NOT NULL, 
	caregiver_id VARCHAR(36) NOT NULL, 
	severity VARCHAR(20) NOT NULL, 
	title VARCHAR(120) NOT NULL, 
	summary TEXT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	acknowledged_at TIMESTAMP WITH TIME ZONE, 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	feedback_label VARCHAR(30), 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (risk_event_id, caregiver_id), 
	FOREIGN KEY(family_id) REFERENCES families (id), 
	FOREIGN KEY(risk_event_id) REFERENCES risk_events (id), 
	FOREIGN KEY(caregiver_id) REFERENCES users (id)
)

;
CREATE INDEX ix_alerts_family_id ON alerts (family_id);
CREATE INDEX ix_alerts_caregiver_id ON alerts (caregiver_id);


CREATE TABLE notifications (
	alert_id VARCHAR(36) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	attempts INTEGER NOT NULL, 
	id VARCHAR(36) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (alert_id), 
	FOREIGN KEY(alert_id) REFERENCES alerts (id)
)

;
