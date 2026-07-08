from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('conventions', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PreloadedExpenseItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('category', models.CharField(choices=[('ACCOM', 'Accommodation'), ('FOOD', 'Food'), ('STAFF', 'Catering Staff'), ('EQUIP', 'Equipment/Logistics'), ('TRANS', 'Transport'), ('SPEAK', 'Speaker Tokens'), ('SECAD', 'Security & Admin'), ('PRINT', 'Stationery/Printing'), ('SUPP', 'Support'), ('PREPOST', 'Pre/Post Convention'), ('MISC', 'Miscellaneous')], max_length=10)),
                ('default_unit', models.CharField(blank=True, default='', max_length=50)),
            ],
            options={'db_table': 'preloaded_expense_items', 'ordering': ['category', 'name']},
        ),
        migrations.CreateModel(
            name='BudgetExpenseItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_code', models.CharField(max_length=30)),
                ('item_name', models.CharField(max_length=200)),
                ('category', models.CharField(choices=[('ACCOM', 'Accommodation'), ('FOOD', 'Food'), ('STAFF', 'Catering Staff'), ('EQUIP', 'Equipment/Logistics'), ('TRANS', 'Transport'), ('SPEAK', 'Speaker Tokens'), ('SECAD', 'Security & Admin'), ('PRINT', 'Stationery/Printing'), ('SUPP', 'Support'), ('PREPOST', 'Pre/Post Convention'), ('MISC', 'Miscellaneous')], max_length=10)),
                ('unit', models.CharField(blank=True, default='', max_length=50)),
                ('estimated_qty', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('unit_price', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('days', models.IntegerField(default=1)),
                ('estimated_total', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('is_custom', models.BooleanField(default=False)),
                ('is_unbudgeted', models.BooleanField(default=False)),
                ('created_by_id', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('convention_unit', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='budget_expenses', to='conventions.conventionunit')),
            ],
            options={'db_table': 'budget_expense_items', 'ordering': ['category', 'item_code']},
        ),
        migrations.CreateModel(
            name='ActualExpense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('actual_qty', models.DecimalField(decimal_places=2, max_digits=10)),
                ('actual_unit_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('actual_total', models.DecimalField(decimal_places=2, max_digits=12)),
                ('authorized_by', models.CharField(max_length=100)),
                ('received_by', models.CharField(max_length=100)),
                ('entered_by_id', models.IntegerField()),
                ('entered_by_name', models.CharField(max_length=100)),
                ('voucher_number', models.CharField(max_length=10)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('notes', models.TextField(blank=True, default='')),
                ('budget_expense_item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='actual_expenses', to='budget.budgetexpenseitem')),
            ],
            options={'db_table': 'actual_expenses', 'ordering': ['timestamp']},
        ),
        migrations.CreateModel(
            name='BudgetIncome',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('student', 'Student'), ('kessat', 'Kessat'), ('associate', 'Associate'), ('offering', 'Offering'), ('exhibition', 'Exhibition')], max_length=20)),
                ('estimated_count', models.IntegerField(default=0)),
                ('unit_fee', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('estimated_total', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('convention_unit', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='budget_incomes', to='conventions.conventionunit')),
            ],
            options={'db_table': 'budget_income'},
        ),
    ]