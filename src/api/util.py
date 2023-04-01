"""
Utility functions
"""

from typing import List

from prisma.models import Retailer


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
    # pylint: disable=duplicate-code
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
