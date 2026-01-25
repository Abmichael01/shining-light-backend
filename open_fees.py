import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import FeeType, SessionTerm, Session

def open_fees_for_current_term():
    print("🔓 Opening Fees for Current Term...")
    
    # 1. Get Current Term
    # Assuming the latest session/term is "Current" for this script
    # In reality, this would be set in system settings
    current_session = Session.objects.filter(is_current=True).first()
    if not current_session:
        current_session = Session.objects.last()
        
    current_term = SessionTerm.objects.filter(session=current_session, is_current=True).first()
    if not current_term:
        current_term = SessionTerm.objects.filter(session=current_session).first()
        
    if not current_term:
        print("❌ No Active Session/Term found.")
        return

    print(f"Target Term: {current_session.name} - {current_term.term_name}")

    # 2. Get All Fees
    all_fees = FeeType.objects.all()
    count = 0
    
    for fee in all_fees:
        # Link fee to this term
        if not fee.active_terms.filter(id=current_term.id).exists():
            fee.active_terms.add(current_term)
            fee.save()
            count += 1
            print(f"  - Opened '{fee.name}' for {current_term.term_name}")
            
    print(f"\n✅ Successfully opened {count} fees for {current_session.name} {current_term.term_name}.")

if __name__ == '__main__':
    open_fees_for_current_term()
