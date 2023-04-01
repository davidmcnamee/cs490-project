[![ci](https://github.com/davidmcnamee/cs490-project/actions/workflows/on_push.yaml/badge.svg)](https://github.com/davidmcnamee/cs490-project/actions/workflows/on_push.yaml)

# Sales Forecasting for New Product Launches

This project is a sales forecasting model for new product launches. The model fetches historical product launch data from the company's SQL database and computes an average volume that can be used for forecasting calculations. Users (primarily project managers) will input the following specifications for their product launch:

- The category of the product (e.g. Toothbrush, Coffee Maker, etc.)
- The brand that the product will be launched under (e.g. Crest, Keurig, etc.)
- The contribution margin associated with each sale of the product (e.g. 20%)
- The retail stores where the product will be sold at (e.g. Walmart, Target, etc.), and the associated list price for each store (e.g. $5.99, $6.99, etc.)
- The number of years to forecast out (e.g. 5 years into the future)
- The upfront intitial investment required to launch the product (e.g. $100,000)

From this, the model will query for historical sales data points that are most comparable to the user's input, in order to compute the expected volume. Once expected volume is calculated, the model will compute Retailer Sales Revenue, Manufacturer Sales Revenue, Manufacturer Gross Revenue, Fixed Costs, and Net Revenue.

This is implemented as Custom Google Sheets function that makes an HTTP request to a Flask API in the cloud. Users can use the model by simply calling a special function `PROJECT_SALES` function in their existing spreadsheet. The output is a table of sales and revenue forecasts.


