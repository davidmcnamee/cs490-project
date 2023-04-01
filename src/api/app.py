"""
API called from google sheets custom function,
that enables the user to calculate the predicted NPV and IRR
for a new product launch (based on historical and external data)
"""
import json
from dataclasses import dataclass
from typing import Any, Dict, List

import numpy_financial as npf
from flask import Flask, request
from prisma import Prisma
from prisma.models import ProductRetailerYear, Retailer

from api.prices import get_average_price

app = Flask(__name__)


def create_template_sheet(retailers: List[Retailer], num_years: int):
    """
    Creates a matrix that can be used as a template spreadsheet. This
    only includes the headings for rows/columns in the spreadsheet, as
    data is later inserted by the `calc_output` function.
    """
    output: List[List[str | float | int]] = [
        ["" for _ in range(2 + num_years)]
        for _ in range(len(retailers) * 20 + 100)  # we trim empty rows at the end
    ]

    def place_header(header_title, include_retailers=False, include_total=False):
        nonlocal row_num
        output[row_num][0] = header_title
        row_num += 1
        offset = row_num if include_retailers else row_num - 1
        if include_retailers:
            for retailer in retailers:
                output[row_num][0] = retailer.name
                row_num += 1
            if include_total:
                output[row_num][0] = "TOTAL"
                row_num += 1
        row_num += 1
        return offset

    # Launch Year
    row_num = 0
    output[row_num][0] = "Launch Year:"
    for i in range(num_years):
        output[row_num][1 + i] = f"Year {i+1}"
    output[row_num][num_years + 1] = "Total"
    row_num += 2

    # Volume
    volume_offset = place_header(
        "Volume (SKUs Sold)", include_retailers=True, include_total=True
    )

    # Retailer Price
    retailer_price_offset = place_header("Retailer's Price", include_retailers=True)

    # Retailer Sales Revenue
    retailer_sales_offset = place_header(
        "Retailer's Sales Revenue", include_retailers=True, include_total=True
    )

    # Manufacturer Sales Revenue
    manufacturer_sales_offset = place_header(
        "Manufacturer's Sales Revenue", include_retailers=True, include_total=True
    )

    # Manufacturer Gross Revenue
    manufacturer_gross_offset = place_header(
        "Manufacturer's Gross Revenue", include_retailers=True, include_total=True
    )

    # Fixed Costs
    fixed_costs_offset = place_header(
        "Fixed Costs", include_retailers=True, include_total=True
    )

    # Net Revenue
    net_revenue_offset = place_header("Net Revenue")

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
    offsets = (
        volume_offset,
        retailer_price_offset,
        retailer_sales_offset,
        manufacturer_sales_offset,
        manufacturer_gross_offset,
        fixed_costs_offset,
        net_revenue_offset,
    )
    return output, offsets


@dataclass
class RetailerTotals:
    """
    Accumulates totals per retailer (i.e. per row in the output spreadsheet)
    """

    total_volume: float = 0
    total_retailer_sales_revenue: float = 0
    total_manufacturer_sales_revenue: float = 0
    total_manufacturer_gross_revenue: float = 0
    total_fixed_costs: float = 0
    total_net_revenue: float = 0


# pylint: disable=too-many-locals disable=too-many-arguments disable=too-many-statements
async def calc_output(
    product_category: str,
    product_brand: str,
    contribution_margin: float,
    retailer_to_list_price: Dict[str, float],
    num_years: int,
    desired_irr: float,
    inital_investment: float,
    relevant_contribution_margin_range: float,
    relevant_list_price_range: float,
):
    """
    Main function: computes spreadsheet of predicted sales data
    for a new product with given parameters.
    """
    num_retailers = len(retailer_to_list_price)
    db = Prisma()  # pylint: disable=invalid-name
    await db.connect()
    try:
        retailers = await db.retailer.find_many(
            where={"name": {"in": list(retailer_to_list_price.keys())}}
        )
        output, offsets = create_template_sheet(retailers, num_years)
        (
            volume_offset,
            retailer_price_offset,
            retailer_sales_offset,
            manufacturer_sales_offset,
            manufacturer_gross_offset,
            fixed_costs_offset,
            net_revenue_offset,
        ) = offsets

        retailer_totals = [RetailerTotals() for _ in retailers + [None]]
        cashflows = [-inital_investment]

        for j, year in enumerate(range(1, num_years + 1)):
            total_volume = 0
            total_retailer_sales_revenue = 0
            total_manufacturer_sales_revenue = 0
            total_manufacturer_gross_revenue = 0
            total_fixed_costs = 0
            for i, retailer in enumerate(retailers):
                list_price = retailer_to_list_price.get(
                    retailer.name, await get_average_price(product_category)
                )
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
                    list_price * (1 - relevant_list_price_range),
                    list_price * (1 + relevant_list_price_range),
                    product_brand,
                    product_category,
                    model=ProductRetailerYear,
                )

                volume = (
                    # pylint: disable=consider-using-generator
                    sum([d.volume_sold for d in data_points]) / len(data_points)
                    if data_points
                    else 0
                )
                retailer_price = list_price * (1 + contribution_margin)
                retailer_sales_revenue = volume * retailer_price
                manufacturer_sales_revenue = volume * list_price
                manufacturer_gross_revenue = (
                    manufacturer_sales_revenue * contribution_margin
                )
                fixed_costs = inital_investment

                total_volume += volume
                total_retailer_sales_revenue += retailer_sales_revenue
                total_manufacturer_sales_revenue += manufacturer_sales_revenue
                total_manufacturer_gross_revenue += manufacturer_gross_revenue
                total_fixed_costs += fixed_costs

                retailer_totals[i].total_volume += volume
                retailer_totals[
                    i
                ].total_retailer_sales_revenue += retailer_sales_revenue
                retailer_totals[
                    i
                ].total_manufacturer_sales_revenue += manufacturer_sales_revenue
                retailer_totals[
                    i
                ].total_manufacturer_gross_revenue += manufacturer_gross_revenue
                retailer_totals[i].total_fixed_costs += fixed_costs

                output[volume_offset + i][j + 1] = volume
                output[retailer_price_offset + i][j + 1] = retailer_price
                output[retailer_sales_offset + i][j + 1] = retailer_sales_revenue
                output[manufacturer_sales_offset + i][
                    j + 1
                ] = manufacturer_sales_revenue
                output[manufacturer_gross_offset + i][
                    j + 1
                ] = manufacturer_gross_revenue
                output[fixed_costs_offset + i][j + 1] = fixed_costs
                output[volume_offset + i][j + 1] = volume

            net_revenue = total_manufacturer_gross_revenue - total_fixed_costs

            output[volume_offset + num_retailers][j + 1] = total_volume
            output[retailer_sales_offset + num_retailers][
                j + 1
            ] = total_retailer_sales_revenue
            output[manufacturer_sales_offset + num_retailers][
                j + 1
            ] = total_manufacturer_sales_revenue
            output[manufacturer_gross_offset + num_retailers][
                j + 1
            ] = total_manufacturer_gross_revenue
            output[fixed_costs_offset + num_retailers][j + 1] = total_fixed_costs
            output[net_revenue_offset][j + 1] = net_revenue

            retailer_totals[-1].total_volume += total_volume
            retailer_totals[
                -1
            ].total_retailer_sales_revenue += total_retailer_sales_revenue
            retailer_totals[
                -1
            ].total_manufacturer_sales_revenue += total_manufacturer_sales_revenue
            retailer_totals[
                -1
            ].total_manufacturer_gross_revenue += total_manufacturer_gross_revenue
            retailer_totals[-1].total_fixed_costs += total_fixed_costs
            retailer_totals[-1].total_net_revenue += net_revenue

            cashflows.append(net_revenue)

        for i, totals in enumerate(retailer_totals):
            output[volume_offset + i][num_years + 1] = totals.total_volume
            output[retailer_sales_offset + i][
                num_years + 1
            ] = totals.total_retailer_sales_revenue
            output[manufacturer_sales_offset + i][
                num_years + 1
            ] = totals.total_manufacturer_sales_revenue
            output[manufacturer_gross_offset + i][
                num_years + 1
            ] = totals.total_manufacturer_gross_revenue
            output[fixed_costs_offset + i][num_years + 1] = totals.total_fixed_costs

        output[net_revenue_offset][num_years + 1] = retailer_totals[
            -1
        ].total_net_revenue

        npv = npf.npv(desired_irr, cashflows)
        irr = npf.irr(cashflows)
        output[net_revenue_offset + 3][1] = npv
        output[net_revenue_offset + 4][1] = irr
        if npv < 0:
            output[net_revenue_offset + 5][
                1
            ] = "Project is not Financially Viable. Reject."
        elif irr < desired_irr:
            output[net_revenue_offset + 5][
                1
            ] = "Project is Financially Viable, but does not meet desired IRR. Reject."
        else:
            output[net_revenue_offset + 5][1] = "Project is Financially Viable. Accept."

        return output
    finally:
        await db.disconnect()


@app.route("/", methods=["GET"])
async def compute_sheet():
    """
    API route to compute the spreadsheet, called by custom function in Google Sheets.
    """
    json_data = request.args.get("json_data")
    assert json_data, "No data provided"
    data = json.loads(json_data)
    output = await calc_output(
        product_category=data["product_category"],
        product_brand=data["product_brand"],
        contribution_margin=data["contribution_margin"],
        retailer_to_list_price=matrix_to_mapping(data["retailer_to_list_price"]),
        num_years=data["num_years"],
        desired_irr=data["desired_irr"],
        inital_investment=data["inital_investment"],
        relevant_contribution_margin_range=data["relevant_contribution_margin_range"],
        relevant_list_price_range=data["relevant_list_price_range"],
    )
    return output


def matrix_to_mapping(matrix: List[List[Any]]) -> Dict[str, Any]:
    """
    Converts a matrix of values into a dictionary that maps from the
    first column to the 2nd column.
    """
    m, n = len(matrix), len(matrix[0])  # pylint: disable=invalid-name
    assert n == 2, "Mappings must have 2 columns"
    mapping = {}
    for i in range(m):
        mapping[matrix[i][0]] = matrix[i][1]
    return mapping


if __name__ == "__main__":
    app.run(host="0.0.0.0")
