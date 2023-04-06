"""
Calculates the predicted sales data and returns as a spreadsheet.
"""

import sys
from dataclasses import dataclass
from typing import Dict, Tuple, Literal

import numpy as np
import numpy_financial as npf
from prisma import Prisma
from prisma.models import ProductRetailerYear, RetailerYear

from api.prices import get_average_price
from api.util import create_template_sheet


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
    variable_cost: float,
    retailers_mapping: Dict[str, Tuple[bool, float | Literal[""]]],
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
    enabled_retailers = [k for k, v in retailers_mapping.items() if v[0] == True]
    num_retailers = len(enabled_retailers)
    db = Prisma()  # pylint: disable=invalid-name
    await db.connect()
    try:
        retailers = await db.retailer.find_many(
            where={"name": {"in": enabled_retailers}}
        )
        discovered_retailers = {r.name for r in retailers}
        missing = [r for r in enabled_retailers if r not in discovered_retailers]
        assert not missing, f"Couldn't find {missing} in database, please ask finance department to input data for this retailer."
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
                retailer_agreements = await db.query_raw(
                    """
                    SELECT *
                    FROM RetailerYear
                    WHERE retailer_id = ?
                    AND year = ?
                    """,
                    retailer.id,
                    year,
                    model=RetailerYear
                )
                retailer_agreement = retailer_agreements[0]
                
                if retailer.name in retailers_mapping and isinstance(retailers_mapping[retailer.name][1], float):
                    list_price = float(retailers_mapping[retailer.name][1])
                else:
                    list_price = (await get_average_price(product_category)) / (1+ retailer_agreement.retailer_markup)

                contribution_margin = (list_price - variable_cost) / list_price
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
                retailer_price = list_price * (1 + retailer_agreement.retailer_markup)
                retailer_sales_revenue = volume * retailer_price
                manufacturer_sales_revenue = volume * list_price
                manufacturer_gross_revenue = (
                    manufacturer_sales_revenue * contribution_margin
                )
                fixed_costs = (
                    retailer_agreement.display_costs +
                    retailer_agreement.priority_shelving_costs +
                    retailer_agreement.preferred_vendor_agreement_costs)

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
        print('old irr: ', irr, file=sys.stderr)
        if np.isnan(irr):
            irr = -999999999
        print('new irr: ', irr, file=sys.stderr)
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

        print('output: ', output, file=sys.stderr)
        return output
    finally:
        await db.disconnect()
