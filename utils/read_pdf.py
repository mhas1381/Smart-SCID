import sys
sys.stdout.reconfigure(encoding='utf-8')
import fitz
import os

pdf_dir = r'c:\Users\Mohammad Husein\Documents\Smart-SCID'
for f in os.listdir(pdf_dir):
    if f.endswith('.pdf') and 'Guide' in f:
        path = os.path.join(pdf_dir, f)
        doc = fitz.open(path)
        
        # Search for differential diagnosis / mood sections
        keywords = ['Differential', 'DIFFERENTIAL', 'differential', 'Bipolar', 'BIPOLAR',
                    'Schizophrenia', 'SCHIZOPHRENIA', 'Schizoaffective', 'SCHIZOAFFECTIVE',
                    'Delusional', 'DELUSIONAL', 'Brief Psychotic', 'BRIEF PSYCHOTIC',
                    'Mood', 'MOOD', 'Depressive', 'DEPRESSIVE']
        
        for i in range(doc.page_count):
            page = doc[i]
            text = page.get_text()
            for kw in keywords:
                if kw in text:
                    print(f'=== Page {i}: found "{kw}" ===')
                    print(text[:800])
                    print()
                    break
        break
