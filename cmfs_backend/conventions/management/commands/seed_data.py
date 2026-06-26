from django.core.management.base import BaseCommand
from conventions.models import Region, County
from budget.models import PreloadedExpenseItem


REGIONS_AND_COUNTIES = [
    ("Central", [
        ("Nyandarua", "NYA"), ("Nyeri", "NYE"), ("Kirinyaga", "KIR"),
        ("Murang'a", "MUR"), ("Kiambu", "KMB"),
    ]),
    ("Coast", [
        ("Mombasa", "MSA"), ("Kwale", "KWL"), ("Kilifi", "KLF"),
        ("Tana River", "TNR"), ("Lamu", "LAM"), ("Taita-Taveta", "TAV"),
    ]),
    ("Eastern", [
        ("Marsabit", "MRB"), ("Isiolo", "ISL"), ("Meru", "MER"),
        ("Tharaka-Nithi", "THN"), ("Embu", "EMB"), ("Kitui", "KTU"),
        ("Machakos", "MAC"), ("Makueni", "MAK"),
    ]),
    ("Nairobi", [
        ("Nairobi", "NBI"),
    ]),
    ("North Eastern", [
        ("Garissa", "GAR"), ("Wajir", "WAJ"), ("Mandera", "MND"),
    ]),
    ("Nyanza", [
        ("Siaya", "SIA"), ("Kisumu", "KSM"), ("Homa Bay", "HOM"),
        ("Migori", "MIG"), ("Kisii", "KSI"), ("Nyamira", "NYM"),
    ]),
    ("Rift Valley", [
        ("Turkana", "TRK"), ("West Pokot", "WPK"), ("Samburu", "SAM"),
        ("Trans Nzoia", "TRN"), ("Uasin Gishu", "UAS"), ("Elgeyo-Marakwet", "ELG"),
        ("Nandi", "NAN"), ("Baringo", "BAR"), ("Laikipia", "LKP"),
        ("Nakuru", "NAK"), ("Narok", "NAR"), ("Kajiado", "KAJ"),
        ("Kericho", "KER"), ("Bomet", "BOM"),
    ]),
    ("Western", [
        ("Kakamega", "KAK"), ("Vihiga", "VIH"), ("Bungoma", "BUN"), ("Busia", "BUS"),
    ]),
]


PRELOADED_EXPENSE_ITEMS = [
    # Accommodation
    ("Student Accommodation", "ACCOM", "per person"),
    ("Associate Accommodation", "ACCOM", "per person"),
    ("Guest House", "ACCOM", "per night"),
    # Food
    ("Milk", "FOOD", "litres"),
    ("Mursik", "FOOD", "litres"),
    ("Bread", "FOOD", "loaves"),
    ("Sugar", "FOOD", "kg"),
    ("Biscuits", "FOOD", "packets"),
    ("Eggs", "FOOD", "trays"),
    ("Tea Leaves", "FOOD", "kg"),
    ("Coffee", "FOOD", "kg"),
    ("Chocolate", "FOOD", "kg"),
    ("Jam", "FOOD", "jars"),
    ("Zesta", "FOOD", "packets"),
    ("Blue Band", "FOOD", "kg"),
    ("Ndegu", "FOOD", "kg"),
    ("Peas", "FOOD", "kg"),
    ("Irish Potatoes", "FOOD", "kg"),
    ("Rice", "FOOD", "kg"),
    ("Maize Meal", "FOOD", "kg"),
    ("Wheat Flour", "FOOD", "kg"),
    ("Beans", "FOOD", "kg"),
    ("Meat", "FOOD", "kg"),
    ("Granding Cost", "FOOD", "lump sum"),
    ("Chicken", "FOOD", "pieces"),
    ("Cabbage", "FOOD", "heads"),
    ("Kienyeji", "FOOD", "kg"),
    ("Sukuma Wiki", "FOOD", "bundles"),
    ("Cooking Oil", "FOOD", "litres"),
    ("Salt", "FOOD", "kg"),
    ("Tomatoes", "FOOD", "kg"),
    ("Oranges", "FOOD", "pieces"),
    ("Bananas", "FOOD", "bunches"),
    ("Watermelon", "FOOD", "pieces"),
    ("Pineapples", "FOOD", "pieces"),
    ("Dania/Capsicum", "FOOD", "kg"),
    ("Carrots", "FOOD", "kg"),
    ("Onions", "FOOD", "kg"),
    ("Royco/Ingredients", "FOOD", "packets"),
    ("Sodas", "FOOD", "crates"),
    ("Mineral Water", "FOOD", "crates"),
    ("Serviettes", "FOOD", "packets"),
    ("Aluminum Foil", "FOOD", "rolls"),
    ("Cling Film", "FOOD", "rolls"),
    ("Firewood", "FOOD", "bundles"),
    ("Gas Refilling", "FOOD", "cylinders"),
    ("Detergents", "FOOD", "kg"),
    ("Liquid Soap", "FOOD", "litres"),
    ("Soap", "FOOD", "bars"),
    ("Hand Wash", "FOOD", "litres"),
    ("Steel Wool", "FOOD", "pieces"),
    ("Toiletries/Vim", "FOOD", "pieces"),
    ("Tissue Papers", "FOOD", "rolls"),
    ("Toothpicks", "FOOD", "packets"),
    ("Garlic", "FOOD", "kg"),
    ("Ginger", "FOOD", "kg"),
    # Catering Staff
    ("Catering Staff", "STAFF", "persons"),
    ("Cleaners", "STAFF", "persons"),
    ("Cateress/Assistant", "STAFF", "persons"),
    ("Head Cook", "STAFF", "persons"),
    ("Plumber", "STAFF", "persons"),
    # Equipment/Logistics
    ("PA System Hire", "EQUIP", "days"),
    ("Generator Fuel", "EQUIP", "litres"),
    ("Tents", "EQUIP", "pieces"),
    ("Plastic Seats", "EQUIP", "pieces"),
    ("Exhibition Tents", "EQUIP", "pieces"),
    ("Dias", "EQUIP", "pieces"),
    ("Decorations", "EQUIP", "lump sum"),
    ("Electric Extension", "EQUIP", "pieces"),
    ("Electronics", "EQUIP", "lump sum"),
    # Transport
    ("Buses", "TRANS", "trips"),
    ("Vehicle Fuel & Maintenance", "TRANS", "litres"),
    ("Transport from/to HQ", "TRANS", "lump sum"),
    ("Local Transport", "TRANS", "lump sum"),
    ("NAM to Chania", "TRANS", "lump sum"),
    ("Driver Appreciation", "TRANS", "persons"),
    # Speaker Tokens
    ("Expositor Token", "SPEAK", "persons"),
    ("Student Speakers", "SPEAK", "persons"),
    ("Associate Speakers", "SPEAK", "persons"),
    ("Kessat Speakers", "SPEAK", "persons"),
    ("Sunday School Speakers", "SPEAK", "persons"),
    ("Praise & Worship Team", "SPEAK", "persons"),
    ("Envelopes", "SPEAK", "pieces"),
    # Security & Admin
    ("Police", "SECAD", "persons"),
    ("Watchmen", "SECAD", "persons"),
    ("Airtime", "SECAD", "lump sum"),
    ("Medication", "SECAD", "lump sum"),
    ("Opening Ceremony", "SECAD", "lump sum"),
    ("Boarding Personnel", "SECAD", "persons"),
    ("Groundsmen", "SECAD", "persons"),
    ("M-Pesa Transaction Costs", "SECAD", "lump sum"),
    # Stationery/Printing
    ("Convention Bible Study Guide", "PRINT", "pieces"),
    ("Meal Cards", "PRINT", "pieces"),
    ("Kessat Meal Cards", "PRINT", "pieces"),
    ("Associate Meal Cards", "PRINT", "pieces"),
    ("Name Tags", "PRINT", "pieces"),
    ("Certificates", "PRINT", "pieces"),
    ("Purchase of Receipts", "PRINT", "books"),
    ("Stationeries & Photocopy", "PRINT", "lump sum"),
    ("Pens", "PRINT", "pieces"),
    ("Roll-Up Banners", "PRINT", "pieces"),
    ("Hall & Gate Banners", "PRINT", "pieces"),
    ("Tear Drops", "PRINT", "pieces"),
    ("Convention Posters", "PRINT", "pieces"),
    ("Video & Photography", "PRINT", "lump sum"),
    ("Note Books", "PRINT", "pieces"),
    # Support
    ("Support to HQ", "SUPP", "lump sum"),
    ("Sunday School Kids (Candle)", "SUPP", "lump sum"),
    # Pre/Post Convention
    ("Pre-Convention Expenses", "PREPOST", "lump sum"),
    ("Post-Convention Expenses", "PREPOST", "lump sum"),
    # Miscellaneous (5% auto-calculated — included here for completeness)
    ("Miscellaneous (5%)", "MISC", "auto"),
]


class Command(BaseCommand):
    help = 'Seed regions, counties and preloaded expense items'

    def handle(self, *args, **options):
        self._seed_regions_and_counties()
        self._seed_expense_items()

    def _seed_regions_and_counties(self):
        self.stdout.write("Seeding regions and counties...")
        for region_name, counties in REGIONS_AND_COUNTIES:
            region, created = Region.objects.get_or_create(name=region_name)
            if created:
                self.stdout.write(f"  Created region: {region_name}")
            for county_name, county_code in counties:
                county, created = County.objects.get_or_create(
                    county_code=county_code,
                    defaults={'name': county_name, 'region': region}
                )
                if created:
                    self.stdout.write(f"    Created county: {county_name} ({county_code})")
        total_regions = Region.objects.count()
        total_counties = County.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Done: {total_regions} regions, {total_counties} counties."
        ))

    def _seed_expense_items(self):
        self.stdout.write("Seeding preloaded expense items...")
        created_count = 0
        for name, category, default_unit in PRELOADED_EXPENSE_ITEMS:
            _, created = PreloadedExpenseItem.objects.get_or_create(
                name=name,
                category=category,
                defaults={'default_unit': default_unit}
            )
            if created:
                created_count += 1
        total = PreloadedExpenseItem.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Done: {created_count} new items created. Total: {total} expense items."
        ))