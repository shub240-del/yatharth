"""Synthetic, assistant-authored proposals. No model predictions used to assign labels.
Translations require native-speaker review. All domains use reserved .invalid.
"""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).parent
VERSION='yatharth-v02-synthetic-1.0'
rows=[]
def add(group,bucket,level,category,signals,en,hi,hg,rationale=''):
 for language,message in [('English',en),('Hindi',hi),('Hinglish',hg)]:
  rows.append(dict(id=f'{group}-{language.lower()}',group_id=group,language=language,message=message,expected_risk_level=level,expected_category=category,expected_signals=signals.split(',') if signals else [],caregiver_escalation_expected=None if level=='AMBIGUOUS' else level in ('HIGH','CRITICAL'),buckets=bucket.split(','),source_type='SYNTHETIC',source='Assistant-authored; no private messages or external corpus',dataset_version=VERSION,variant='canonical',parent_id=None,label_rationale=rationale or ('Routine or educational content with no actionable coercion.' if category=='NONE' else 'Provisional escalation label based on message semantics; not proof of fraud.'),reviewer_1=None,reviewer_2=None,final_label=None,agreement=None,label_status='UNREVIEWED',split='challenge',context_available=False))
# A: legitimate family
add('A01','A','LOW','NONE','', 'Dad, the vegetables are in the kitchen.','पापा, सब्जियाँ रसोई में रखी हैं।','Papa, sabziyan rasoi mein rakhi hain.')
add('A02','A','LOW','NONE','', 'Mum, I reached the station safely.','माँ, मैं स्टेशन सुरक्षित पहुँच गया हूँ।','Maa, main station safely pahunch gaya hoon.')
add('A03','A','LOW','NONE','', 'Your daughter will call after her exam.','आपकी बेटी परीक्षा के बाद फोन करेगी।','Aapki beti exam ke baad call karegi.')
add('A04','A','LOW','NONE','', 'Please bring my spectacles when you visit.','मिलने आएँ तो मेरा चश्मा ले आइए।','Milne aao toh mera chashma le aana.')
add('A05','A','LOW','NONE','', 'The family lunch is postponed until Sunday.','परिवार का दोपहर का भोजन रविवार तक टल गया है।','Family lunch Sunday tak postpone ho gaya hai.')
# B: legitimate financial discussions and receipts
add('B01','B','LOW','NONE','', 'The rent transfer has already cleared; nothing remains to pay.','किराए का भुगतान हो चुका है; अब कुछ देना बाकी नहीं है।','Rent transfer ho chuka hai; ab kuch pay nahi karna.')
add('B02','B','LOW','NONE','', 'Please compare the two fixed-deposit rates before deciding.','फैसला करने से पहले दोनों सावधि जमा की दरें देख लें।','Decision se pehle dono fixed deposit rates compare kar lena.')
add('B03','B','LOW','NONE','', 'I am reviewing our monthly grocery budget.','मैं हमारे महीने के राशन का बजट देख रहा हूँ।','Main monthly grocery budget dekh raha hoon.')
add('B04','B','LOW','NONE','', 'This investment may lose value; returns are not guaranteed.','इस निवेश में नुकसान हो सकता है; लाभ की गारंटी नहीं है।','Is investment mein loss ho sakta hai; returns guaranteed nahi hain.')
add('B05','B','LOW','NONE','', 'We bought gift cards yesterday; the payment receipt is attached.','हमने कल उपहार कार्ड खरीदे थे; भुगतान की रसीद साथ है।','Humne kal gift cards kharide the; payment receipt attached hai.')
# C: bank/payment safety advice
add('C01','C','LOW','NONE','', 'Your monthly account statement is available in your banking app.','आपका मासिक खाता विवरण आपके बैंकिंग ऐप में उपलब्ध है।','Aapka monthly account statement banking app mein hai.')
add('C02','C','LOW','NONE','', 'Security tip: no bank employee needs your OTP or password.','सुरक्षा सलाह: बैंक कर्मचारी को आपके ओटीपी या पासवर्ड की जरूरत नहीं होती।','Safety tip: bank employee ko aapka OTP ya password nahi chahiye.')
add('C03','C','LOW','NONE','', 'Payment of ₹800 was successful. This is a receipt, not a request.','₹800 का भुगतान सफल हुआ। यह रसीद है, भुगतान का अनुरोध नहीं।','₹800 payment successful tha. Yeh receipt hai, request nahi.')
add('C04','C','LOW','NONE','', 'Never send money to avoid arrest; police do not collect fines on video calls.','गिरफ्तारी से बचने के लिए कभी पैसे न भेजें; पुलिस वीडियो कॉल पर जुर्माना नहीं लेती।','Arrest se bachne ke liye kabhi paise mat bhejo; police video call par fine nahi leti.')
add('C05','C','LOW','NONE','', 'Scam awareness: criminals may say your account is blocked today and ask you to transfer money immediately. Report such messages.','ठगी से सावधान: अपराधी कह सकते हैं कि आज खाता बंद होगा और तुरंत पैसे भेजने को कह सकते हैं। ऐसे संदेश की शिकायत करें।','Scam awareness: criminals bol sakte hain account aaj blocked hai aur turant money transfer karo. Aise message report karo.')
# D: healthcare updates, no private patient data
add('D01','D','LOW','NONE','', 'The clinic moved your consultation to Thursday morning.','क्लिनिक ने आपकी मुलाकात गुरुवार सुबह कर दी है।','Clinic ne consultation Thursday morning kar diya hai.')
add('D02','D','LOW','NONE','', 'The hospital has received the deposit; no further payment is due.','अस्पताल को जमा राशि मिल गई है; अब कोई भुगतान बाकी नहीं है।','Hospital ko deposit mil gaya; ab payment due nahi hai.')
add('D03','D','LOW','NONE','', 'Please carry your old prescription to the appointment.','डॉक्टर से मिलने पर पुराना पर्चा साथ लाएँ।','Appointment par purani prescription le aana.')
add('D04','D','LOW','NONE','', 'Your son is resting after a minor accident. We are together and no money is needed.','आपका बेटा मामूली दुर्घटना के बाद आराम कर रहा है। हम साथ हैं और पैसे की जरूरत नहीं है।','Aapka beta chhote accident ke baad rest kar raha hai. Hum saath hain, money nahi chahiye.')
add('D05','D','LOW','NONE','', 'The health camp is free. Do not share your bank details with anyone claiming a registration fee.','स्वास्थ्य शिविर मुफ्त है। पंजीकरण शुल्क माँगने वाले को बैंक की जानकारी न दें।','Health camp free hai. Registration fee maangne wale ko bank details mat do.')
# Q: insufficient context; excluded from binary performance, not counted as negatives
ambiguous=[
('Can you send ₹500?','क्या आप ₹500 भेज सकते हैं?','Kya aap ₹500 bhej sakte ho?'),
('Please call me urgently.','कृपया मुझे तुरंत फोन करें।','Please mujhe urgently call karo.'),
('The bank needs a document.','बैंक को एक दस्तावेज चाहिए।','Bank ko ek document chahiye.'),
('Someone says there is an account issue.','कोई कह रहा है कि खाते में समस्या है।','Koi keh raha hai account mein issue hai.'),
('Open this link when you can: https://example.invalid/info','समय मिले तो यह लिंक खोलें: https://example.invalid/info','Time mile toh yeh link kholo: https://example.invalid/info'),
('I need help at the hospital.','मुझे अस्पताल में मदद चाहिए।','Mujhe hospital mein help chahiye.'),
('The parcel requires verification.','पार्सल के लिए सत्यापन चाहिए।','Parcel ke liye verification chahiye.'),
('Keep the birthday plan secret from Mum.','जन्मदिन की योजना माँ से छिपाकर रखना।','Birthday plan Maa se secret rakhna.')]
for n,(en,hi,hg) in enumerate(ambiguous,1): add(f'Q{n:02}','Q','AMBIGUOUS','UNKNOWN','',en,hi,hg,'Insufficient evidence to distinguish benign intent from a risky request; do not force a binary truth label.')
# E–N: three different message scenarios per risk category, each in three languages.
add('E01','E,P','HIGH','FINANCIAL_SCAM','FINANCIAL_REQUEST,URGENCY,SECRECY','Buy ₹4000 of gift cards immediately and keep this secret.','तुरंत ₹4000 के उपहार कार्ड खरीदें और इसे गुप्त रखें।','Abhi ₹4000 ke gift cards kharido aur kisi ko mat batana.')
add('E02','E','HIGH','PHISHING','CREDENTIAL_REQUEST,SUSPICIOUS_LINK,URGENCY','Enter your password today at https://login-prize.invalid to collect the prize.','इनाम लेने के लिए आज https://login-prize.invalid पर अपना पासवर्ड डालें।','Prize lene ke liye aaj https://login-prize.invalid par password daalo.')
add('E03','E','MEDIUM','FINANCIAL_SCAM','FINANCIAL_REQUEST','Please send money to the new wallet for the fee.','कृपया शुल्क के लिए नए वॉलेट में पैसे भेजें।','Please fee ke liye naye wallet mein paise bhejo.')
add('F01','F,P','HIGH','CREDENTIAL_THEFT','CREDENTIAL_REQUEST,URGENCY,SECRECY','Send your OTP immediately and do not tell your family.','अपना ओटीपी तुरंत भेजें और परिवार को न बताएँ।','Apna OTP turant bhejo aur family ko mat batana.')
add('F02','F','HIGH','CREDENTIAL_THEFT','CREDENTIAL_REQUEST,URGENCY,UNUSUAL_REQUEST','Share your PIN and CVV right now to receive a refund; we do not need the card.','रिफंड पाने के लिए अपना पिन और सीवीवी अभी बताएँ; कार्ड की जरूरत नहीं है।','Refund ke liye apna PIN aur CVV abhi batao; card nahi chahiye.')
add('F03','F','MEDIUM','CREDENTIAL_THEFT','CREDENTIAL_REQUEST','Kindly tell me the verification code you just received.','कृपया अभी मिला सत्यापन कोड मुझे बताएँ।','Abhi jo verification code aaya hai, please mujhe batao.')
add('G01','G','HIGH','BANK_IMPERSONATION','IMPERSONATION,AUTHORITY_CLAIM,CREDENTIAL_REQUEST','I am a bank officer. Give me your password for verification.','मैं बैंक अधिकारी हूँ। सत्यापन के लिए अपना पासवर्ड दीजिए।','Main bank officer hoon. Verification ke liye password do.')
add('G02','G','HIGH','BANK_IMPERSONATION','ACCOUNT_THREAT,URGENCY,FINANCIAL_REQUEST','Your account will be frozen today. Transfer ₹9000 immediately to unlock it.','आज आपका खाता बंद हो जाएगा। खोलने के लिए तुरंत ₹9000 भेजें।','Aaj account freeze ho jayega. Unlock karne ke liye turant ₹9000 transfer karo.')
add('G03','G','HIGH','BANK_IMPERSONATION','AUTHORITY_CLAIM,ACCOUNT_THREAT,CREDENTIAL_REQUEST','Your KYC has expired. Provide your bank details and OTP for renewal.','आपका केवाईसी समाप्त हो गया है। नवीनीकरण के लिए बैंक विवरण और ओटीपी दें।','Aapka KYC expire ho gaya. Renewal ke liye bank details aur OTP do.')
add('H01','H,P','CRITICAL','GOVERNMENT_IMPERSONATION','AUTHORITY_CLAIM,LEGAL_THREAT,FINANCIAL_REQUEST,SECRECY','The tax department will prosecute you. Transfer money and do not contact anyone.','कर विभाग आप पर मुकदमा करेगा। पैसे भेजें और किसी से संपर्क न करें।','Tax department case karega. Paise transfer karo aur kisi se contact mat karo.')
add('H02','H','HIGH','GOVERNMENT_IMPERSONATION','AUTHORITY_CLAIM,FINANCIAL_REQUEST,URGENCY','RBI instructs you to send ₹7000 immediately to release your pension.','पेंशन जारी करने के लिए आरबीआई आपको तुरंत ₹7000 भेजने को कहता है।','Pension release ke liye RBI turant ₹7000 bhejne ko bolta hai.')
add('H03','H','HIGH','GOVERNMENT_IMPERSONATION','IMPERSONATION,AUTHORITY_CLAIM,CREDENTIAL_REQUEST','I am a government officer. Give me the OTP for your Aadhaar benefit.','मैं सरकारी अधिकारी हूँ। आधार लाभ के लिए मुझे ओटीपी दें।','Main government officer hoon. Aadhaar benefit ke liye OTP do.')
add('I01','I','HIGH','COURIER_SCAM','AUTHORITY_CLAIM,FINANCIAL_REQUEST,URGENCY','Customs holds your parcel. Pay ₹600 immediately or it will be destroyed.','सीमा शुल्क विभाग ने पार्सल रोका है। तुरंत ₹600 दें, वरना उसे नष्ट कर देंगे।','Customs ne parcel rok liya. Turant ₹600 pay karo warna destroy kar denge.')
add('I02','I','HIGH','COURIER_SCAM','FINANCIAL_REQUEST,SUSPICIOUS_LINK,URGENCY','Your courier package needs a fee today. Send payment at https://verify-parcel.invalid.','आपके कूरियर पार्सल के लिए आज शुल्क चाहिए। https://verify-parcel.invalid पर भुगतान भेजें।','Courier parcel ke liye aaj fee chahiye. https://verify-parcel.invalid par payment bhejo.')
add('I03','I','HIGH','COURIER_SCAM','CREDENTIAL_REQUEST,UNUSUAL_REQUEST','To deliver your parcel, please provide your card PIN and CVV to the courier agent.','पार्सल पहुँचाने के लिए कूरियर एजेंट को कार्ड का पिन और सीवीवी दें।','Parcel deliver karne ke liye courier agent ko card PIN aur CVV do.')
add('J01','J','HIGH','TECH_SUPPORT_SCAM','UNUSUAL_REQUEST,FINANCIAL_REQUEST,URGENCY','Install AnyDesk today and send ₹3000 to remove the virus from your phone.','आज एनीडेस्क लगाएँ और फोन का वायरस हटाने के लिए ₹3000 भेजें।','Aaj AnyDesk install karo aur phone ka virus hatane ke liye ₹3000 bhejo.')
add('J02','J,P','HIGH','TECH_SUPPORT_SCAM','UNUSUAL_REQUEST,SECRECY,URGENCY','Enable remote access immediately. Keep this secret from your family.','तुरंत दूरस्थ पहुँच चालू करें। यह बात परिवार से गुप्त रखें।','Turant remote access chalu karo. Family se secret rakhna.')
add('J03','J','HIGH','TECH_SUPPORT_SCAM','IMPERSONATION,UNUSUAL_REQUEST,CREDENTIAL_REQUEST','This is tech support. Start screen sharing and enter your bank password so we can fix your phone.','यह तकनीकी सहायता है। स्क्रीन साझा करें और फोन ठीक करने के लिए बैंक पासवर्ड डालें।','Yeh tech support hai. Screen share karo aur phone fix karne ke liye bank password daalo.')
add('K01','K','HIGH','INVESTMENT_SCAM','FINANCIAL_REQUEST,URGENCY,UNUSUAL_REQUEST','Guaranteed returns of 40% daily. Send ₹5000 immediately to join this investment.','रोज 40% मुनाफे की गारंटी। निवेश में शामिल होने के लिए तुरंत ₹5000 भेजें।','Roz 40% return guaranteed. Investment join karne ke liye turant ₹5000 bhejo.')
add('K02','K,P','HIGH','INVESTMENT_SCAM','UNUSUAL_REQUEST,FINANCIAL_REQUEST,SECRECY','Double your money with our investment. Buy crypto and do not tell anyone.','हमारे निवेश से पैसा दोगुना करें। क्रिप्टो खरीदें और किसी को न बताएँ।','Hamare investment se paisa double karo. Crypto kharido aur kisi ko mat batao.')
add('K03','K','MEDIUM','INVESTMENT_SCAM','UNUSUAL_REQUEST','This investment promises guaranteed returns, with no other details.','यह निवेश बिना किसी अन्य जानकारी के निश्चित लाभ का वादा करता है।','Yeh investment guaranteed returns bolta hai, aur details nahi hain.')
add('L01','L,O','HIGH','FAMILY_EMERGENCY_IMPERSONATION','EMOTIONAL_PRESSURE,FINANCIAL_REQUEST,URGENCY','Your daughter is injured. Send ₹8000 immediately to the hospital wallet.','आपकी बेटी घायल है। अस्पताल के वॉलेट में तुरंत ₹8000 भेजें।','Aapki beti injured hai. Hospital wallet mein turant ₹8000 bhejo.')
add('L02','L,O,P','CRITICAL','FAMILY_EMERGENCY_IMPERSONATION','EMOTIONAL_PRESSURE,FINANCIAL_REQUEST,URGENCY,SECRECY','Dad, I had an accident. Transfer ₹20000 immediately and do not call my usual number or tell Mum.','पापा, मेरा एक्सीडेंट हुआ है। तुरंत ₹20000 भेजें और मेरे पुराने नंबर पर फोन न करें या माँ को न बताएँ।','Papa, mera accident ho gaya. Turant ₹20000 transfer karo; mere usual number par call mat karo aur Maa ko mat batao.')
add('L03','L,O','HIGH','FAMILY_EMERGENCY_IMPERSONATION','EMOTIONAL_PRESSURE,FINANCIAL_REQUEST,UNUSUAL_REQUEST','I am your son using a new number. I cannot speak. The surgeon needs gift cards before treating me.','मैं आपका बेटा नए नंबर से बोल रहा हूँ। बात नहीं कर सकता। इलाज से पहले सर्जन को उपहार कार्ड चाहिए।','Main aapka beta naye number se hoon. Bol nahi sakta. Treatment se pehle surgeon ko gift cards chahiye.')
add('M01','M,P','CRITICAL','DIGITAL_ARREST_SCAM','AUTHORITY_CLAIM,LEGAL_THREAT,SECRECY,FINANCIAL_REQUEST,URGENCY','Police digital arrest order: stay on the video call, do not tell family, and transfer money immediately.','पुलिस का डिजिटल गिरफ्तारी आदेश: वीडियो कॉल पर रहें, परिवार को न बताएँ और तुरंत पैसे भेजें।','Police ka digital arrest order: video call par raho, family ko mat batao, turant paise transfer karo.')
add('M02','M,P','CRITICAL','DIGITAL_ARREST_SCAM','AUTHORITY_CLAIM,LEGAL_THREAT,SECRECY,FINANCIAL_REQUEST','CBI has an arrest warrant. This is a confidential investigation; pay ₹30000 to close the case.','सीबीआई के पास गिरफ्तारी वारंट है। यह गोपनीय जाँच है; मामला बंद करने के लिए ₹30000 दें।','CBI ke paas arrest warrant hai. Confidential investigation hai; case close karne ke liye ₹30000 pay karo.')
add('M03','M,P','CRITICAL','DIGITAL_ARREST_SCAM','AUTHORITY_CLAIM,LEGAL_THREAT,SECRECY,CREDENTIAL_REQUEST','Your Aadhaar is linked to a crime. Police require your OTP. Do not inform your family; remain on camera.','आपका आधार अपराध से जुड़ा है। पुलिस को आपका ओटीपी चाहिए। परिवार को न बताएँ; कैमरे पर रहें।','Aadhaar crime se linked hai. Police ko OTP chahiye. Family ko inform mat karo; camera par raho.')
add('N01','N','HIGH','PHISHING','SUSPICIOUS_LINK,CREDENTIAL_REQUEST,URGENCY','Verify your password now at https://secure-login.invalid; access expires today.','https://secure-login.invalid पर अभी पासवर्ड सत्यापित करें; आज पहुँच समाप्त हो जाएगी।','https://secure-login.invalid par abhi password verify karo; access aaj expire hoga.')
add('N02','N','MEDIUM','PHISHING','SUSPICIOUS_LINK','View your unclaimed reward: https://claim-reward.invalid.','अपना बिना लिया इनाम देखें: https://claim-reward.invalid।','Apna unclaimed reward dekho: https://claim-reward.invalid.')
add('N03','N','HIGH','PHISHING','CREDENTIAL_REQUEST,SUSPICIOUS_LINK,URGENCY','Enter your OTP immediately at http://192.0.2.10/login to stop a charge.','शुल्क रोकने के लिए http://192.0.2.10/login पर तुरंत अपना ओटीपी डालें।','Charge rokne ke liye http://192.0.2.10/login par turant OTP daalo.')
# R: paired adversarial variants; keep scenario family IDs for cluster-aware analysis.
import copy,re
seeds=['E01','F01','G01','H01','I01','J01','K01','L01','M01','N01']
for group in seeds:
 base=next(r for r in rows if r['id']==group+'-english')
 for kind in ['keyword_removed','misspelling','mixed_language','polite','indirect','implied_urgency','implied_authority','late_request']:
  r=copy.deepcopy(base);r['id']=group+'-adv-'+kind;r['parent_id']=base['id'];r['variant']=kind;r['buckets']=list(dict.fromkeys(base['buckets']+['R']))
  text=base['message']
  if kind=='keyword_removed':
   for a,b in [('password','sign-in secret'),('OTP','six-digit number that just arrived'),('money','the requested amount'),('transfer','move'),('Send','Forward'),('send','forward'),('immediately','before this session closes'),('Police','Law-enforcement desk'),('police','law-enforcement desk'),('arrest','detention'),('gift cards','prepaid store vouchers'),('bank officer','account-services representative'),('AnyDesk','the remote-control application'),('pay','settle'),('Pay','Settle'),('Guaranteed returns','Assured daily profits')]:text=text.replace(a,b)
  elif kind=='misspelling':
   for a,b in [('OTP','0 T P'),('password','p@ssw0rd'),('money','m0ney'),('bank','b4nk'),('Police','P0lice'),('transfer','tr@nsfer'),('immediately','immediatly'),('Send','S3nd'),('send','s3nd'),('gift cards','g1ft c@rds')]:text=text.replace(a,b)
  elif kind=='mixed_language':
   text=next(x['message'] for x in rows if x['id']==group+'-hinglish')+' Please follow these instructions.';r['language']='Hinglish'
  elif kind=='polite':text='Good morning. If you would be so kind, '+text[0].lower()+text[1:];text=text.replace('immediately','at your earliest convenience')
  elif kind=='indirect':text='To complete the process, it would help if you could '+text[0].lower()+text[1:]
  elif kind=='implied_urgency':text=re.sub(r'\b(immediately|today|now)\b','before this session closes',text,flags=re.I)+' This is the final available session.'
  elif kind=='implied_authority':text='Message from the case compliance desk: '+text;text=re.sub(r'\b(bank officer|Police|police|tax department|Customs|CBI)\b','assigned representative',text)
  elif kind=='late_request':
   r['conversation_turns']=['Hello. Please remain available while I locate your file.',text]
   r['context_available']=True;text='[Earlier] '+r['conversation_turns'][0]+'\n[Later] '+text
  r['message']=text;r['label_rationale']='Semantic-preserving challenge transformation proposed by the author; human equivalence review pending.'
  rows.append(r)
# Six exploratory Marathi examples; no claim of regional-language support.
regional=[('LOW','NONE',False,'औषधांची आठवण करून दे.','','D'),('LOW','NONE',False,'बँकेचे मासिक विवरण ॲपमध्ये उपलब्ध आहे.','','C'),('LOW','NONE',False,'मी सुरक्षित घरी पोहोचलो आहे.','','A'),('HIGH','CREDENTIAL_THEFT',True,'तुमचा ओटीपी लगेच पाठवा आणि घरच्यांना सांगू नका.','CREDENTIAL_REQUEST,URGENCY,SECRECY','F,P'),('CRITICAL','DIGITAL_ARREST_SCAM',True,'पोलीस आदेश आहे. अटक टाळण्यासाठी ताबडतोब पैसे पाठवा आणि कुणालाही सांगू नका.','AUTHORITY_CLAIM,LEGAL_THREAT,FINANCIAL_REQUEST,URGENCY,SECRECY','M,P'),('HIGH','FAMILY_EMERGENCY_IMPERSONATION',True,'तुमच्या मुलीला अपघात झाला आहे. रुग्णालयात ताबडतोब आठ हजार रुपये पाठवा.','EMOTIONAL_PRESSURE,FINANCIAL_REQUEST,URGENCY','L,O')]
for n,(level,cat,esc,message,signals,bucket) in enumerate(regional,1):
 r=copy.deepcopy(rows[0]);r.update(id=f'REG{n:02}-marathi',group_id=f'REG{n:02}',language='Marathi',message=message,expected_risk_level=level,expected_category=cat,expected_signals=signals.split(',') if signals else [],caregiver_escalation_expected=esc,buckets=bucket.split(','),label_rationale='Exploratory synthetic Marathi translation; native-speaker and safety review pending.');rows.append(r)
assert len(rows)==260,len(rows)
assert len({r['id'] for r in rows})==len(rows)
assert len({r['message'] for r in rows})==len(rows)
(ROOT/'cases.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
manifest={'version':VERSION,'cases':len(rows),'author':'AI assistant','all_labels':'PROVISIONAL, not human ground truth','sha256':hashlib.sha256((ROOT/'cases.json').read_bytes()).hexdigest(),'engine_tuning_on_this_set':False,'independent_human_review_count':0,'split':'challenge-only; no trained/tuned model and no held-out validity claim','scenario_groups':len({r['group_id'] for r in rows})}
(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(manifest)
