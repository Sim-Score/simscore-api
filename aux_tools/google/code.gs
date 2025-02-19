function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu("SimScore")
    .addItem("Analyze with SimScore", "showColumnSelector")
    .addItem("Set API Key", "showApiKeyDialog")
    .addItem("Clear API Key", "clearApiKey")
    .addToUi();
}

function showColumnSelector() {
  // Get all column headers from the active sheet
  const sheet = SpreadsheetApp.getActiveSheet();
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];

  // Create HTML template for column selection
  const template = HtmlService.createTemplateFromFile("ColumnSelector");
  template.headers = headers;

  // Show modal dialog
  const html = template.evaluate().setWidth(400).setHeight(300);

  SpreadsheetApp.getUi().showModalDialog(html, "Select Columns for Analysis");
}

function showApiKeyDialog() {
  const ui = SpreadsheetApp.getUi();
  const result = ui.prompt(
    "SimScore API Key",
    "Enter your API key:",
    ui.ButtonSet.OK_CANCEL
  );

  if (result.getSelectedButton() == ui.Button.OK) {
    const apiKey = result.getResponseText();
    PropertiesService.getScriptProperties().setProperty(
      "SIMSCORE_API_KEY",
      apiKey
    );
    ui.alert("API key saved successfully");
  }
}

function clearApiKey() {
  PropertiesService.getScriptProperties().deleteProperty("SIMSCORE_API_KEY");
  SpreadsheetApp.getUi().alert("API key cleared");
}

function getApiKey() {
  return PropertiesService.getScriptProperties().getProperty(
    "SIMSCORE_API_KEY"
  );
}

function getApiUrl() {
  return PropertiesService.getScriptProperties().getProperty(
    "SIMSCORE_API_URL"
  ) || 'https://simscore-api-dev.fly.dev/v1/rank_ideas';
}

function processSelectedColumns(
  selections = { idColumn: "ID#", ideaColumn: "ideas", authorColumn: "author" }
) {
  const sheet = SpreadsheetApp.getActiveSheet();
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  console.log("Column selection: ", selections);
  // Get column indices
  const ideaColIndex = headers.indexOf(selections.ideaColumn) + 1;
  const idColIndex = selections.idColumn
    ? headers.indexOf(selections.idColumn) + 1
    : null;
  const authorColIndex = selections.authorColumn
    ? headers.indexOf(selections.authorColumn) + 1
    : null;

  // Get all data
  const lastRow = sheet.getLastRow();
  const ideas = [];

  console.log(`Analysing Rows 2 - ${lastRow}`)

  // Build data array
  for (let row = 2; row <= lastRow; row++) {
    ideaValue = sheet.getRange(row, ideaColIndex).getValue()
    if (!ideaValue) continue;
    const idea = {
      idea: ideaValue,
    };
    
    if (idColIndex) {
      idea.id = sheet.getRange(row, idColIndex).getValue().toString();
    }
    
    if (authorColIndex) {
      idea.author_id = sheet.getRange(row, authorColIndex).getValue();
    }

    if (row % 50 === 0) {
      console.log(`Row ${row}: `, idea)
    }
    
    ideas.push(idea);
  }

  // Process with SimScore API
  const requestData = {
    ideas: ideas,
    advanced_features: {
      pairwise_similarity_matrix: true,
      relationship_graph: true,
      cluster_names: true,
    },
  };

  const response = callSimScoreApi(requestData);
  if (response) {
    console.log("(Slices of) Ranked Ideas: \b", response.ranked_ideas.slice(0, 5), "\n[...]\n", response.ranked_ideas.slice(-10));
    console.log("Has similarity matrix? : ", Boolean(response.pairwise_similarity_matrix));
    console.log("Has cluster names? : ", Boolean(response.cluster_names));
    displayResults(response);
  }
}

function callSimScoreApi(requestData) {
  const API_URL = getApiUrl();
  const apiKey = getApiKey();

  const options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(requestData),
  };
  if (apiKey) {
    options["headers"] = { Authorization: `Bearer ${apiKey}` };
  }

  const forLogging = JSON.stringify(options)
  console.log("Options: ", forLogging.slice(0, 200) + "\n[...]\n" + forLogging.slice(forLogging.length/2, forLogging.length/2+200) + "\n[...]\n" + forLogging.slice(-700, -500)); // the last 400chars or so is the API key
  try {
    const response = UrlFetchApp.fetch(API_URL, options);
    return JSON.parse(response.getContentText());
  } catch (error) {
    SpreadsheetApp.getUi().alert(
      "Error calling SimScore API: " + error.toString()
    );
    return null;
  }
}

function displayResults(response) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  // Create Rankings Sheet
  let rankingsSheet = ss.getSheetByName("SimScore Rankings");
  if (rankingsSheet) {
    rankingsSheet.clear();
  } else {
    rankingsSheet = ss.insertSheet("SimScore Rankings");
  }

  // Headers for rankings
  const headers = [
    "Priority",
    "ID",
    "Idea",
    "Author",
    "Similarity Score",
    "Cluster",
  ];
  rankingsSheet.getRange(1, 1, 1, headers.length).setValues([headers]);

  // Format ranked ideas
  const rankedData = response.ranked_ideas.map((item, index) => {
    const clusterName =
      response.cluster_names?.find((c) => c.id === item.cluster_id)?.name || item.cluster_id;
    return [
      "# " + (index + 1),
      item.id,
      item.idea,
      item.author_id || "",
      item.similarity_score,
      clusterName,
    ];
  });

  console.log("Ranked Data: ", rankedData.slice(0,5), rankedData.slice(-5))

  if (rankedData.length > 0) {
    rankingsSheet
      .getRange(2, 1, rankedData.length, rankedData[0].length)
      .setValues(rankedData);
  }


  if (response.relationship_graph) {
    createScatterPlot(response, rankingsSheet, rankedData);
  }

  // Create Matrix Sheet if available
  if (response.pairwise_similarity_matrix) {
    let matrixSheet = ss.getSheetByName("SimScore Matrix");
    if (matrixSheet) {
      matrixSheet.clear();
    } else {
      matrixSheet = ss.insertSheet("SimScore Matrix");
    }

    const matrix = response.pairwise_similarity_matrix;
    const ids = response.ranked_ideas.map((item) => item.id).concat("Centroid");

    // Create header row with IDs
    const headerRow = ["ID"] // top-left corner
      .concat(ids); // IDs

    // Add ID column to each row
    const matrixWithHeaders = matrix.map((row, index) => {
      return [ids[index]].concat(row);
    });

    // Combine headers and matrix
    const fullMatrix = [headerRow].concat(matrixWithHeaders);
    console.log("Matrix:\n\n", fullMatrix.slice(0, 5), fullMatrix.slice(-5));

    // Important: Use the fullMatrix dimensions which include the headers
    const numRows = fullMatrix.length;
    const numCols = fullMatrix[0].length;

    console.log("Matrix Rows/Cols: ", numRows, numCols);

    // Set values
    matrixSheet.getRange(1, 1, numRows, numCols).setValues(fullMatrix);

    // Format headers
    matrixSheet.getRange(1, 1, 1, numCols).setFontWeight("bold");
    matrixSheet.getRange(1, 1, numRows, 1).setFontWeight("bold");

    // Apply heatmap only to the actual matrix values (excluding headers)
    const rule = SpreadsheetApp.newConditionalFormatRule()
      .setGradientMaxpoint("#4285f4") // Blue
      .setGradientMinpoint("#fbbc04") // Yellow
      .setRanges([matrixSheet.getRange(2, 2, matrix.length, matrix[0].length)])
      .build();

    matrixSheet.setConditionalFormatRules([rule]);
  }
}

function createScatterPlot(response, sheet, rankedData) {
  // Data for the chart - in required API order
  const chartData = [["X", "Y", "ID", "Similarity"]];
  const colorMap = {};
  response.relationship_graph.nodes.forEach((node, index) => {
    const idea = response.ranked_ideas.find((i) => i.id === node.id);
    const similarity = idea ? idea.similarity_score : 1.0;

    // Add data point
    chartData.push([
      node.coordinates.x,
      node.coordinates.y,
      node.id.toString(),
      similarity,
    ]);

    // Calculate color using index instead of ID
    const t = similarity;
    let color = "#" +
        Math.round(251 - 185 * t).toString(16).padStart(2, "0") +
        Math.round(188 - 55 * t).toString(16).padStart(2, "0") +
        Math.round(4 + 240 * t).toString(16).padStart(2, "0")
    
    colorMap[index] = { color };
  });
  
  console.log(colorMap.slice(0, 5), colorMap.slice(-5));

  const chartRange = sheet.getRange(1, rankedData[0].length, chartData.length, chartData[0].length);
  chartRange.setValues(chartData);
  sheet.hideColumns(chartRange.getColumn(), chartRange.getNumColumns());

  const chart = sheet
    .newChart()
    .setChartType(Charts.ChartType.BUBBLE)
    .addRange(chartRange)
    .setOption("title", "Similarity to the most similar point")
    .setOption("height", 600)
    .setOption("width", 800)
    .setOption("series", colorMap)
    .setPosition(3, chartRange.getColumn() + chartRange.getNumColumns() + 1, 0, 0)
    .build();
  sheet.insertChart(chart);
}
