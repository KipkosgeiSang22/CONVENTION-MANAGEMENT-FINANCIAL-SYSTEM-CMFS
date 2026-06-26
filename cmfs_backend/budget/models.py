from django.db import models


class BudgetIncome(models.Model):
    CATEGORY_CHOICES = [
        ('student', 'Student'),
        ('kessat', 'Kessat'),
        ('associate', 'Associate'),
        ('offering', 'Offering'),
        ('exhibition', 'Exhibition'),
    ]

    convention_unit = models.ForeignKey(
        'conventions.ConventionUnit',
        on_delete=models.PROTECT,
        related_name='budget_incomes'
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    estimated_count = models.IntegerField(default=0)
    unit_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estimated_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = 'budget_income'

    def __str__(self):
        return f"BudgetIncome — {self.category} (unit {self.convention_unit_id})"


class PreloadedExpenseItem(models.Model):
    """Master list of the 50+ standard expense items. Seeded once. Never changed by users."""
    CATEGORY_CHOICES = [
        ('ACCOM', 'Accommodation'),
        ('FOOD', 'Food'),
        ('STAFF', 'Catering Staff'),
        ('EQUIP', 'Equipment/Logistics'),
        ('TRANS', 'Transport'),
        ('SPEAK', 'Speaker Tokens'),
        ('SECAD', 'Security & Admin'),
        ('PRINT', 'Stationery/Printing'),
        ('SUPP', 'Support'),
        ('PREPOST', 'Pre/Post Convention'),
        ('MISC', 'Miscellaneous'),
    ]

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    default_unit = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        db_table = 'preloaded_expense_items'
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.category})"


class BudgetExpenseItem(models.Model):
    """A budget line item for a specific convention unit — either from the preloaded list or custom."""
    CATEGORY_CHOICES = PreloadedExpenseItem.CATEGORY_CHOICES

    convention_unit = models.ForeignKey(
        'conventions.ConventionUnit',
        on_delete=models.PROTECT,
        related_name='budget_expenses'
    )
    item_code = models.CharField(max_length=30)  # EXP-FOOD-001 or UNB-FOOD-001
    item_name = models.CharField(max_length=200)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    unit = models.CharField(max_length=50, blank=True, default='')
    estimated_qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    days = models.IntegerField(default=1)
    estimated_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_custom = models.BooleanField(default=False)
    is_unbudgeted = models.BooleanField(default=False)
    created_by_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'budget_expense_items'
        ordering = ['category', 'item_code']

    def __str__(self):
        return f"{self.item_code} — {self.item_name}"


class ActualExpense(models.Model):
    """Actual spend recorded against a budgeted or unbudgeted expense item."""
    budget_expense_item = models.ForeignKey(
        BudgetExpenseItem,
        on_delete=models.PROTECT,
        related_name='actual_expenses'
    )
    actual_qty = models.DecimalField(max_digits=10, decimal_places=2)
    actual_unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    actual_total = models.DecimalField(max_digits=12, decimal_places=2)
    authorized_by = models.CharField(max_length=100)   # typed — not from JWT
    received_by = models.CharField(max_length=100)     # typed — not from JWT
    entered_by_id = models.IntegerField()              # from JWT — never typed
    entered_by_name = models.CharField(max_length=100) # from JWT — never typed
    voucher_number = models.CharField(max_length=10)   # PV01, PV02 ... per unit
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'actual_expenses'
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.voucher_number} — {self.budget_expense_item.item_name}"