"""
TEHTEK — Supporting files for finance extended module

─────────────────────────────────────────────────────────────────────────────
1. app/core/enums.py  — add these entries to your existing SequenceType enum
─────────────────────────────────────────────────────────────────────────────
"""

# Add to your existing SequenceType enum in app/core/enums.py:
# (these follow the same pattern as invoice_number and receipt_number)
#
#   income_number     = "INC"
#   expense_number    = "EXP"
#   debt_number       = "DEBT"
#   receivable_number = "RCV"
#   autopark_number   = "APK"
#
# Example if you use an Enum class:
#
# class SequenceType(str, Enum):
#     invoice_number    = "INV"
#     receipt_number    = "RCP"
#     income_number     = "INC"     # NEW
#     expense_number    = "EXP"     # NEW
#     debt_number       = "DEBT"    # NEW
#     receivable_number = "RCV"     # NEW
#     autopark_number   = "APK"     # NEW


"""
─────────────────────────────────────────────────────────────────────────────
2. Alembic migration — alembic/versions/xxxx_finance_extended.py
─────────────────────────────────────────────────────────────────────────────
Run:  alembic revision --autogenerate -m "finance_extended"
Then: alembic upgrade head

The autogenerate will pick up all new models as long as they are imported
in env.py. Add this line to alembic/env.py:

    from app.modules.finance.models_extended import (   # noqa: F401
        MoneyAccount, Income, FinanceExpense, Location,
        Debt, DebtPayment, Receivable, ReceivablePayment,
        BudgetLine, Vehicle, AutoParkRecord,
    )

─────────────────────────────────────────────────────────────────────────────
3. app/main.py — register the new routers
─────────────────────────────────────────────────────────────────────────────

    from app.modules.finance.router_extended import router as finance_ext_router
    from app.modules.finance.router_extended import ap_router

    app.include_router(finance_ext_router)
    app.include_router(ap_router)

─────────────────────────────────────────────────────────────────────────────
4. Permission strings (add to your permission registry)
─────────────────────────────────────────────────────────────────────────────

Required permissions used in router_extended.py:

    finance:accounts
    finance:income
    finance:expenses
    finance:approve_expense
    finance:locations
    finance:debt
    finance:receivables
    finance:write_off
    finance:budget
    finance:customer_balances
    finance:summary
    autopark:view
    autopark:manage

─────────────────────────────────────────────────────────────────────────────
5. Business rules summary (for your backend developer)
─────────────────────────────────────────────────────────────────────────────

MoneyAccount.current_balance:
  • Incremented when Income.status = "received" is saved
  • Decremented when FinanceExpense.status = "paid" is saved
  • Never set manually by the user
  • Shown on the finance overview as cash/bank/mobile_money balance

DebtPayment cascade (POST /finance/debt/payments):
  1. Create FinanceExpense(category="debt_repayment", ref_model="debt", ref_label=debt_number)
  2. Reduce Debt.outstanding by payment amount
  3. Debit MoneyAccount.current_balance
  4. If outstanding <= 0: Debt.status = "paid_off"
  5. Update Debt.last_payment_date and last_payment_amount

ReceivablePayment cascade (POST /finance/receivables/payments):
  1. Create Income (auto-generated income_number)
  2. Increase Receivable.paid_amount by payment amount
  3. Reduce Receivable.balance_due = amount - paid_amount
  4. Reduce Customer.outstanding_balance by payment amount
  5. Credit MoneyAccount.current_balance
  6. If balance_due <= 0: Receivable.status = "collected"
  7. Else: Receivable.status = "partial"

AutoParkRecord release (POST /autopark/records/{id}/release):
  1. Set exit_date
  2. duration_days = (exit_date - entry_date).days (min 1)
  3. total_amount  = parking_rate × duration_days
  4. balance_due   = total_amount - paid_amount
  5. If balance_due > 0: create Receivable(ref_model="autopark")
  6. Vehicle.status = "released"

Expense ref_model enforcement:
  • ref_model and ref_label are REQUIRED on FinanceExpense
  • The API validator rejects any expense where ref_model is null or empty
  • The category "debt_repayment" is auto-created — users cannot create it manually

Income ref_model rule:
  • ref_model may be null ONLY for category = "capital_injection"
  • All other categories require a ref_model + ref_label

Budget reconciliation:
  • spent_amount on BudgetLine is NOT updated in real time
  • Run a background task or endpoint to recompute:
      UPDATE budget_lines bl SET
        spent_amount = (
          SELECT COALESCE(SUM(amount_base), 0) FROM finance_expenses
          WHERE company_id = bl.company_id
            AND category = bl.category
            AND EXTRACT(YEAR  FROM date) = bl.period_year
            AND EXTRACT(MONTH FROM date) = bl.period_month
            AND deleted_at IS NULL AND status = 'paid'
        ),
        variance = budget_amount - spent_amount,
        variance_pct = CASE WHEN budget_amount > 0
          THEN (budget_amount - spent_amount) / budget_amount * 100 ELSE 0 END,
        updated_at = NOW()
      WHERE company_id = :company_id
        AND period_year = :year AND period_month = :month;
"""