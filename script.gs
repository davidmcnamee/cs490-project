
/**
 * Compute the projected profitability of a new product launch
 * using historical sales data and external product pricing APIs.
 * 
 * @param {string} product_category The new product's category
 * @param {string} product_brand The brand that the new product will be sold under
 * @param {number} variable_cost The new product's variable cost per unit
 * @param {Array<Array<string|boolean|number>>} retailers_mapping A table that maps each retailer name to a boolean (whether it's enabled or not), and a number representing the list price for that retailer
 * @param {number} num_years The number of years to forecast out
 * @param {number} desired_irr The desired internal rate of return for this product
 * @param {number} inital_investment The initial upfront investment required for the product
 * @param {number} relevant_contribution_margin_range (Optional) A percentage indicating the range of contribution margins to consider when looking for comparable products
 * @param {number} relevant_list_price_range (Optional) A percentage indicating the range of list prices to consider when looking for comparable products
 * @return A table containing the projected sales data and profitability calculations
 * @customfunction
 */
function FORECAST_SALES(
  product_category,
  product_brand,
  variable_cost,
  retailers_mapping,
  num_years,
  desired_irr,
  inital_investment,
  relevant_contribution_margin_range = 999999999,
  relevant_list_price_range = 999999999,
) {
  var json_data = JSON.stringify({
      product_category,
      product_brand,
      variable_cost,
      retailers_mapping,
      num_years,
      desired_irr,
      inital_investment,
      relevant_contribution_margin_range,
      relevant_list_price_range,
    })
  var arguments = {
    'json_data': json_data,
  }
  var url = buildUrl_("https://cs490.mcnamee.io", arguments)
  var response = UrlFetchApp.fetch(url, { 'muteHttpExceptions': true })
  if(response.getResponseCode() != '200') {
    var message = response.getContentText()
    try {
      message = JSON.parse(response.getContentText())['message']
    } catch {}
    return "Error: " + message
  }
  var deserialized = JSON.parse(response.getContentText())
  return deserialized
}

// Sourced from: https://github.com/googleworkspace/apps-script-oauth2/blob/ade8b9a8c5e8117ea18bcd14fcd1bb779a3425f8/src/Utilities.js#L27
// Used under Apache license from Google Inc.
/**
 * Builds a complete URL from a base URL and a map of URL parameters.
 * @param {string} url The base URL.
 * @param {Object.<string, string>} params The URL parameters and values.
 * @return {string} The complete URL.
 * @private
 */
function buildUrl_(url, params) {
  var paramString = Object.keys(params).map(function(key) {
    return encodeURIComponent(key) + '=' + encodeURIComponent(params[key]);
  }).join('&');
  return url + (url.indexOf('?') >= 0 ? '&' : '?') + paramString;
}

function onOpen() {
  createMenu();
}

function createMenu() {
   var menu = SpreadsheetApp.getUi().createMenu("Forecast Tools");
   menu.addItem("Authenticate", "authenticate");
   menu.addItem("Automatic Formatting", "autoFormat");
   menu.addToUi();
}

function authenticate() {
  SpreadsheetApp.getActive().toast("You selected Setting A.");
}

function autoFormat() {
  var spreadsheet = SpreadsheetApp.getActive();
  var sheet = spreadsheet.getSheets()[0];
  var rangeData = sheet.getDataRange()
  var m = rangeData.getLastRow(), n = rangeData.getLastColumn();
  var searchRange = sheet.getRange(1, 1, m, n);
  var values = searchRange.getValues()
  
  var root_row = 0, root_col = 0;
  var width = 0, height = 0;
  var numRetailers = 0;
  var numYears = 0;

  for (var i = 0; i < m; i++){
    for (var j = 0 ; j < n; j++){
      if(values[i][j] === "Launch Year:"){
        root_row = i; root_col = j;
        var volumeHeading = 0;
        for(var k = i+1; k < m; ++k) {
          if(values[k][j] === "Volume (SKUs Sold)") volumeHeading = k
          if(values[k][j] === "TOTAL" && numRetailers === 0) numRetailers = k-1 - volumeHeading
          if(values[k][j] === 'Recommendation') {
            height = k - (i-1)
            break
          }
        }
        for(var k = j+1; k <= n; ++k) {
          if(k === n || values[i][k] === '') {
            width = k-1 - (j-1)
            break
          }
        }
      }
    }
  }
  numYears = width - 1
  if(width === 0 || height === 0 || numRetailers === 0) return spreadsheet.toast("Couldn't find FORECAST_SALES output anywhere in your sheet.")
  // reset styles initially
  for(var i = root_row; i < root_row+height; ++i) {
    for(var j = root_col; j < root_col+width; ++j) {
      sheet.getRange(i+1, j+1, 1, 1)
        .setFontWeight('normal')
        .setBorder(false, false, false, false, false, false)
        .setBackground(null)
    }
  }  

  sheet.setColumnWidth(root_col+1, 211);
  for(var j = root_col+1; j < root_col+width; ++j) {
    sheet.setColumnWidth(j+1, 100);
  }
  // year headers 
  sheet.getRange(root_row+1, root_col+1+1, 1, width-1)
    .setHorizontalAlignment('center')
    .setFontWeight('bold')    
  // vertical border
  sheet.getRange(root_row+1, root_col+width-1+1, height-5, 1)
    .setBorder(
      false, true, false, false, null, null, null,
      SpreadsheetApp.BorderStyle.SOLID);
  // decision output box
  sheet.getRange(root_row+height-4+1, root_col+1, 4, width)
    .setBorder(true, true, true, true, null, null, null,
      SpreadsheetApp.BorderStyle.SOLID);
  // number formatting
  sheet.getRange(root_row+3+1, root_col+1+1, numRetailers+1, width-1)
    .setNumberFormat("#,##0")
  sheet.getRange(root_row+3+numRetailers+1+1, root_col+1+1, height-5, width-1)
    .setNumberFormat("$#,##0.00")
  sheet.getRange(root_row+height-2+1, root_col+1+1, 1, 1)
    .setNumberFormat("#0.00%")

  var titles = ["Launch Year:", "Volume (SKUs Sold)", "Retailer's Price", "Retailer's Sales Revenue", "Manufacturer's Sales Revenue", "Manufacturer's Gross Revenue", "Fixed Costs", "Net Revenue", "NPV Analysis", "IRR Analysis", "Recommendation"]
  for(var i = root_row; i < root_row+height; ++i) {
    if(values[i][root_col] === "TOTAL") {
      sheet.getRange(i+1, root_col+1, 1, 1).setFontWeight('bold')
      sheet.getRange(i+1, root_col+1, 1, width)
        .setBorder(
          true, false, false, false, null, null, null,
          SpreadsheetApp.BorderStyle.SOLID);
    }
    var isTitle = titles.some(t => values[i][root_col] === t)
    if(isTitle) sheet.getRange(i+1, root_col+1, 1, 1).setFontWeight('bold')
    if(!isTitle && values[i][root_col] !== "DECISION OUTPUT") {
      sheet.getRange(i+1, root_col+1, 1, 1).setHorizontalAlignment('right')
    }
    if(values[i][root_col] === "DECISION OUTPUT") {
      sheet.getRange(i+1, root_col+1, 1, 1).setTextStyle(
        SpreadsheetApp.newTextStyle().setUnderline(true).build()
      )
    }
    if(values[i][root_col] === "Net Revenue") {
      sheet.getRange(i+1, root_col+1, 1, width).setBorder(false, false, true, false, null, null, null, SpreadsheetApp.BorderStyle.DOUBLE);
    }
    if(values[i][root_col] === "Recommendation") {
      var range = sheet.getRange(i+1, root_col+1+1, 1, 4)
      var numbersRange = sheet.getRange(i-2+1, root_col+1+1, 2, 1)
      if(values[i][root_col+1].indexOf("Reject") > -1) {
        numbersRange.setBackground('#E06666') // light red 1
        range.mergeAcross()
          .setBackground('#F4CCCC') // light red 3
          .setFontColor('#CC0000') // dark red 1
          .setFontWeight('bold')
      } else {
        numbersRange.setBackground('#93C47D') // light green 1
        range.mergeAcross()
          .setBackground('green')
          .setFontColor('white')
          .setFontWeight('bold')
      }
    }
  }

}

function equals(range1, range2) {
  return range1.getRow() === range2.getRow() && range1.getColumn() === range2.getColumn()
}
