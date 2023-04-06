"""
API called from google sheets custom function,
that enables the user to calculate the predicted NPV and IRR
for a new product launch (based on historical and external data)
"""
import json
from typing import Any, Dict, List

from flask import Flask, request

from api.calc import calc_output

app = Flask(__name__)


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
        retailers_mapping=matrix_to_mapping(data["retailer_to_list_price"]),
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
    first column to the remaining columns.
    """
    m = len(matrix)  # pylint: disable=invalid-name
    mapping = {}
    for i in range(m):
        mapping[matrix[i][0]] = tuple(matrix[i][1:])
    return mapping


if __name__ == "__main__":
    app.run(host="0.0.0.0")
