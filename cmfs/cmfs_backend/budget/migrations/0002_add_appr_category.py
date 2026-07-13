from django.db import migrations, models


NEW_CATEGORY_CHOICES = [
    ('ACCOM', 'Accommodation'),
    ('FOOD', 'Food'),
    ('STAFF', 'Catering Staff'),
    ('EQUIP', 'Equipment/Logistics'),
    ('TRANS', 'Transport'),
    ('SPEAK', 'Speaker Tokens'),
    ('APPR', 'Workers & Appreciation'),
    ('SECAD', 'Security & Admin'),
    ('PRINT', 'Stationery/Printing'),
    ('SUPP', 'Support'),
    ('PREPOST', 'Pre/Post Convention'),
    ('MISC', 'Miscellaneous'),
]


class Migration(migrations.Migration):
    """
    Adds the 'Workers & Appreciation' (APPR) category, which previously had
    no home — organizing-committee/volunteer appreciation payouts had no
    category distinct from Catering Staff (STAFF) or Speaker Tokens (SPEAK).

    This is a choices-only change (no new column, no data migration needed):
    existing rows are unaffected since APPR is additive, not a rename.
    """

    dependencies = [
        ('budget', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='preloadedexpenseitem',
            name='category',
            field=models.CharField(choices=NEW_CATEGORY_CHOICES, max_length=10),
        ),
        migrations.AlterField(
            model_name='budgetexpenseitem',
            name='category',
            field=models.CharField(choices=NEW_CATEGORY_CHOICES, max_length=10),
        ),
    ]
