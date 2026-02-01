
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
django.setup()

from api.models import Staff, StaffSalary, SalaryPayment, StaffWallet

def check_salary_setup():
    print("--- Checking Staff Salary Setup ---")
    
    staff_members = Staff.objects.all()
    print(f"Total Staff: {staff_members.count()}")
    
    active_staff = Staff.objects.filter(status='active')
    print(f"Active Staff: {active_staff.count()}")
    
    with_salary = Staff.objects.filter(current_salary__isnull=False)
    print(f"Staff with Assigned Salary: {with_salary.count()}")
    
    print("\n--- Detailed Staff List (first 10) ---")
    for staff in staff_members[:10]:
        val = {
            "ID": staff.staff_id,
            "Name": staff.get_full_name(),
            "Status": staff.status,
            "Has_Salary": hasattr(staff, 'current_salary'),
            "Salary_Grade": str(staff.current_salary.salary_grade) if hasattr(staff, 'current_salary') else "None",
            "Wallet_Balance": "N/A",
            "Payments": staff.salary_payments.count()
        }
        
        if hasattr(staff, 'wallet'):
            val["Wallet_Balance"] = staff.wallet.wallet_balance
            
        print(val)

    print("\n--- Recent Salary Payments ---")
    recent = SalaryPayment.objects.order_by('-created_at')[:5]
    for p in recent:
        print(f"Payment: {p.staff.get_full_name()} - {p.month}/{p.year} - Status: {p.status} - Amt: {p.amount}")

if __name__ == "__main__":
    check_salary_setup()
