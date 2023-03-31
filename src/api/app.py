from dataclasses import dataclass
import json
import os
from flask import Flask, request, jsonify
from typing import Dict, List, Optional, Tuple
from prisma import Prisma
from prisma.models import ProductRetailerYear, Retailer
from prisma.types import RetailerWhereInput
from api.stuff import hi
import numpy_financial as npf

app = Flask(__name__)

def create_template_sheet(retailers: List[Retailer], num_years: int):
    output : List[List[str|float|int]] = [
        ["" for _ in range(2+num_years)]
        for _ in range(len(retailers)*20+100) # we trim empty rows at the end
    ]

    # Launch Year
    row_num = 0
    output[row_num][0] = "Launch Year:"
    for i in range(num_years):
        output[row_num][1+i] = f"Year {i+1}"
    output[row_num][num_years+1] = "Total"
    row_num += 2

    # Volume
    output[row_num][0] = "Volume (SKUs Sold)"
    row_num += 1
    volume_offset = row_num
    for i, retailer in enumerate(retailers):
        output[row_num][0] = retailer.name
        row_num += 1
    output[row_num][0] = "TOTAL"
    row_num += 2

    # Retailer Price
    output[row_num][0] = "Retailer's Price"
    row_num += 1
    retailer_price_offset = row_num
    for i, retailer in enumerate(retailers):
        output[row_num][0] = retailer.name
        row_num += 1
    row_num += 1

    # Retailer Sales Revenue
    output[row_num][0] = "Retailer's Sales Revenue"
    row_num += 1
    retailer_sales_offset = row_num
    for i, retailer in enumerate(retailers):
        output[row_num][0] = retailer.name
        row_num += 1
    output[row_num][0] = "TOTAL"
    row_num += 2

    # Manufacturer Sales Revenue
    output[row_num][0] = "Manufacturer's Sales Revenue"
    row_num += 1
    manufacturer_sales_offset = row_num
    for i, retailer in enumerate(retailers):
        output[row_num][0] = retailer.name
        row_num += 1
    output[row_num][0] = "TOTAL"
    row_num += 2

    # Manufacturer Gross Revenue
    output[row_num][0] = "Manufacturer's Gross Revenue"
    row_num += 1
    manufacturer_gross_offset = row_num
    for i, retailer in enumerate(retailers):
        output[row_num][0] = retailer.name
        row_num += 1
    output[row_num][0] = "TOTAL"
    row_num += 2

    # Fixed Costs
    output[row_num][0] = "Fixed Costs"
    row_num += 1
    fixed_costs_offset = row_num
    for i, retailer in enumerate(retailers):
        output[row_num][0] = retailer.name
        row_num += 1
    output[row_num][0] = "TOTAL"
    row_num += 2

    # Net Revenue
    net_revenue_offset = row_num
    output[row_num][0] = "Net Revenue"
    row_num += 2

    # Decision Output
    output[row_num][0] = "DECISION OUTPUT"
    row_num += 1
    output[row_num][0] = "NPV Analysis"
    row_num += 1
    output[row_num][0] = "IRR Analysis"
    row_num += 1
    output[row_num][0] = "Recommendation"
    row_num += 1

    output = output[:row_num]
    offsets = volume_offset, retailer_price_offset, retailer_sales_offset, manufacturer_sales_offset, manufacturer_gross_offset, fixed_costs_offset, net_revenue_offset
    return output, offsets

@dataclass
class RetailerTotals:
    total_volume: float = 0
    total_retailer_sales_revenue: float = 0
    total_manufacturer_sales_revenue: float = 0
    total_manufacturer_gross_revenue: float = 0
    total_fixed_costs: float = 0
    total_net_revenue: float = 0

async def calc_output(
    product_category: str,
    product_brand: str,
    contribution_margin: float,
    retailer_to_list_price: Dict[str, Optional[float]],
    num_years: int,
    desired_irr: float,
    inital_investment: float,
    relevant_contribution_margin_range: float,
    relevant_list_price_range: float,
):
    num_retailers = len(retailer_to_list_price)
    db = Prisma()
    await db.connect()
    try:
        retailers = await db.retailer.find_many(
            where={
                "name": {
                    "in": list(retailer_to_list_price.keys())
                }
            }
        )
        output, offsets = create_template_sheet(retailers, num_years)
        volume_offset, retailer_price_offset, retailer_sales_offset, manufacturer_sales_offset, manufacturer_gross_offset, fixed_costs_offset, net_revenue_offset = offsets

        retailer_totals = [RetailerTotals() for _ in retailers + [None]]
        cashflows = [-inital_investment]

        for j, year in enumerate(range(1, num_years+1)):
            total_volume = 0
            total_retailer_sales_revenue = 0
            total_manufacturer_sales_revenue = 0
            total_manufacturer_gross_revenue = 0
            total_fixed_costs = 0
            for i, retailer in enumerate(retailers):
                list_price = retailer_to_list_price[retailer.name]
                assert list_price # TODO: if None (retailer doesn't have a list price), we should look up in 3rd-party API
                data_points = await db.query_raw(
                    """
                    SELECT *
                    FROM ProductRetailerYear
                    JOIN Product ON Product.id = ProductRetailerYear.product_id
                    WHERE retailer_id = ?
                    AND year = ?
                    AND contribution_margin BETWEEN ? AND ?
                    AND list_price BETWEEN ? AND ?
                    AND Product.brand_name = ?
                    AND Product.category = ?
                    """,
                    retailer.id,
                    year,
                    contribution_margin - relevant_contribution_margin_range,
                    contribution_margin + relevant_contribution_margin_range,
                    list_price*(1-relevant_list_price_range),
                    list_price*(1+relevant_list_price_range),
                    product_brand,
                    product_category,
                    model=ProductRetailerYear,
                )
                app.logger.info("data filters: %s", (retailer.id,
                    year,
                    contribution_margin - relevant_contribution_margin_range,
                    contribution_margin + relevant_contribution_margin_range,
                    list_price - relevant_list_price_range,
                    list_price + relevant_list_price_range,
                    product_brand,
                    product_category,))
                volume = sum([d.volume_sold for d in data_points]) / len(data_points) if data_points else 0
                # list_price either provided by user OR external API (category) => average list_price
                list_price = sum([d.list_price for d in data_points]) / len(data_points) if data_points else 0
                retailer_price = list_price * (1 + contribution_margin)
                retailer_sales_revenue = volume * retailer_price
                manufacturer_sales_revenue = volume * list_price
                manufacturer_gross_revenue = manufacturer_sales_revenue * contribution_margin
                fixed_costs =  inital_investment

                total_volume += volume
                total_retailer_sales_revenue += retailer_sales_revenue
                total_manufacturer_sales_revenue += manufacturer_sales_revenue
                total_manufacturer_gross_revenue += manufacturer_gross_revenue
                total_fixed_costs += fixed_costs
                
                retailer_totals[i].total_volume += volume
                retailer_totals[i].total_retailer_sales_revenue += retailer_sales_revenue
                retailer_totals[i].total_manufacturer_sales_revenue += manufacturer_sales_revenue
                retailer_totals[i].total_manufacturer_gross_revenue += manufacturer_gross_revenue
                retailer_totals[i].total_fixed_costs += fixed_costs

                output[volume_offset + i][j+1] = volume
                output[retailer_price_offset + i][j+1] = retailer_price
                output[retailer_sales_offset + i][j+1] = retailer_sales_revenue
                output[manufacturer_sales_offset + i][j+1] = manufacturer_sales_revenue
                output[manufacturer_gross_offset + i][j+1] = manufacturer_gross_revenue
                output[fixed_costs_offset + i][j+1] = fixed_costs
                output[volume_offset + i][j+1] = volume

            net_revenue = total_manufacturer_gross_revenue - total_fixed_costs
            
            output[volume_offset + num_retailers][j+1] = total_volume
            output[retailer_sales_offset + num_retailers][j+1] = total_retailer_sales_revenue
            output[manufacturer_sales_offset + num_retailers][j+1] = total_manufacturer_sales_revenue
            output[manufacturer_gross_offset + num_retailers][j+1] = total_manufacturer_gross_revenue
            output[fixed_costs_offset + num_retailers][j+1] = total_fixed_costs
            output[net_revenue_offset][j+1] = net_revenue

            retailer_totals[-1].total_volume += total_volume
            retailer_totals[-1].total_retailer_sales_revenue += total_retailer_sales_revenue
            retailer_totals[-1].total_manufacturer_sales_revenue += total_manufacturer_sales_revenue
            retailer_totals[-1].total_manufacturer_gross_revenue += total_manufacturer_gross_revenue
            retailer_totals[-1].total_fixed_costs += total_fixed_costs
            retailer_totals[-1].total_net_revenue += net_revenue

            cashflows.append(net_revenue)

        for i, totals in enumerate(retailer_totals):
            output[volume_offset + i][num_years+1] = totals.total_volume
            output[retailer_sales_offset + i][num_years+1] = totals.total_retailer_sales_revenue
            output[manufacturer_sales_offset + i][num_years+1] = totals.total_manufacturer_sales_revenue
            output[manufacturer_gross_offset + i][num_years+1] = totals.total_manufacturer_gross_revenue
            output[fixed_costs_offset + i][num_years+1] = totals.total_fixed_costs
        
        output[net_revenue_offset][num_years+1] = retailer_totals[-1].total_net_revenue
        
        npv = npf.npv(desired_irr, cashflows)
        irr = npf.irr(cashflows)
        output[net_revenue_offset+3][1] = npv
        output[net_revenue_offset+4][1] = irr
        if npv < 0:
            output[net_revenue_offset+5][1] = "Project is not Financially Viable. Reject."
        elif irr < desired_irr:
            output[net_revenue_offset+5][1] = "Project is Financially Viable, but does not meet desired IRR. Reject."
        else:
            output[net_revenue_offset+5][1] = "Project is Financially Viable. Accept."
        
        return output
    finally:
        await db.disconnect()


@app.route('/', methods=['GET'])
async def compute_sheet():
    json_data = request.args.get('json_data')
    assert json_data, "No data provided"
    data = json.loads(json_data)
    output = await calc_output(
        product_category=data['product_category'],
        product_brand=data['product_brand'],
        contribution_margin=data['contribution_margin'],
        retailer_to_list_price=matrix_to_mapping(data['retailer_to_list_price']),
        num_years=data['num_years'],
        desired_irr=data['desired_irr'],
        inital_investment=data['inital_investment'],
        relevant_contribution_margin_range=data['relevant_contribution_margin_range'],
        relevant_list_price_range=data['relevant_list_price_range'],
    )
    return output

def matrix_to_mapping(matrix):
    m, n = len(matrix), len(matrix[0])
    mapping = {}
    for i in range(m):
        mapping[matrix[i][0]] = matrix[i][1]
    return mapping

if __name__ == '__main__':
    app.run(host='0.0.0.0')
