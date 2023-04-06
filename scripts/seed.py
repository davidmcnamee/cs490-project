# Seeds database with mock data

from prisma import Prisma
from prisma.types import RetailerCreateInput, ProductRetailerYearCreateInput, ProductCreateInput, RetailerYearCreateInput
import asyncio
import random

async def main():
    print('Seeding database with mock data...')
    db = Prisma()
    await db.connect()
    await db.retailer.delete_many()
    await db.product.delete_many()
    await db.productretaileryear.delete_many()
    await db.retaileryear.delete_many()
    retailer_data = [
        ['Walmart', 'USA', 'WMT'],
        ['Loblaws', 'Canada', 'LOB'],
        ["Shopper's Drug Mart", 'Canada', 'SDM'],
        ['Rexall', 'Canada', 'REX'],
        ['Costco', 'Canada', 'COS'],
    ]
    product_data = [
        ['Crest 3D White', 'Toothpaste'],
        ['Crest Pro-Health', 'Toothpaste'],
        ['Crest Complete Plus', 'Toothpaste'],
        ['Crest Kids', 'Toothpaste'],
        ['Crest 3D White', 'Mouthwash'],
        ['Crest Pro-Health', 'Mouthwash'],
        ['Oral-B Kids', 'Toothbrush'],
        ['Oral-B Pro-Health', 'Toothbrush'],
        ['Oral-B iO', 'Toothbrush'],
        ['Crest 3D White', 'Floss'],
        ['Oral-B Kids', 'Floss'],
        ['Oral-B Pro-Health', 'Floss'],
    ]
    await db.retailer.create_many(
        data=[RetailerCreateInput(
            name=row[0],
            country=row[1],
            shorthand=row[2],
        ) for row in retailer_data]
    )
    await db.product.create_many(
        data=[ProductCreateInput(
            brand_name=row[0],
            category=row[1],
        ) for row in product_data]
    )
    retailers = await db.retailer.find_many()
    await db.retaileryear.create_many(
        data = [
        RetailerYearCreateInput(
            retailer_id=retailer.id,
            year=year,
            retailer_markup=random.random() * 0.4,
            display_costs=random.randint(0, 50000),
            priority_shelving_costs=random.randint(0, 50000),
            preferred_vendor_agreement_costs=random.randint(0, 50000),
        )
        for retailer in retailers
        for year in range(1, 8+1)],
        skip_duplicates=True
    )
    products = await db.product.find_many()
    await db.productretaileryear.create_many(
        data = [
        ProductRetailerYearCreateInput(
            retailer_id=retailer.id,
            product_id=product.id,
            year=year,
            volume_sold=random.randint(0, 50000),
            list_price=random.random() * 30.0,
            contribution_margin=random.random() * 0.4,
        )
        for product in products
        for retailer in retailers
        for year in range(1, 8+1)],
        skip_duplicates=True
    )
    print('Done ✨')

asyncio.run(main())
