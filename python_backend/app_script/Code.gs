function onOpen() {
  try {
    // Check if we're in a context where UI is available
    var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    if (!spreadsheet) {
      return; // No active spreadsheet, can't create UI
    }

    var ui = SpreadsheetApp.getUi();
    if (ui) {
      ui.createMenu("AI Copilot")
        .addItem("Open Copilot", "showCopilotSidebar")
        .addToUi();
    }
  } catch (e) {
    // UI not available in this context (e.g., script editor, API execution, or trigger)
    // Silently ignore - this is expected in some contexts
    // Only log if it's an unexpected error
    if (e.toString().indexOf("getUi") === -1) {
      Logger.log("Unexpected error in onOpen: " + e.toString());
    }
  }
}

function showCopilotSidebar() {
  try {
    // Get UI first
    var ui = SpreadsheetApp.getUi();
    if (!ui) {
      Logger.log("UI not available in this context");
      return;
    }

    // Create HTML output with proper settings
    var html = HtmlService.createHtmlOutputFromFile("Sidebar")
      .setTitle("Sheet Mangler")
      .setWidth(400)
      .setSandboxMode(HtmlService.SandboxMode.IFRAME);

    ui.showSidebar(html);
  } catch (e) {
    Logger.log("Error showing sidebar: " + e.toString());
    Logger.log("Error details: " + JSON.stringify(e));

    // Try to show an error message if possible
    try {
      var ui = SpreadsheetApp.getUi();
      if (ui) {
        ui.alert(
          "Error opening sidebar: " +
            e.toString() +
            "\n\nPlease check the execution log for more details."
        );
      }
    } catch (e2) {
      // Can't show alert either, just log
      Logger.log("Cannot show error alert: " + e2.toString());
    }
  }
}

/**
 * Test function to verify HTML file can be loaded.
 * Run this from the script editor to debug HTML loading issues.
 */
function testSidebarHtml() {
  try {
    var html = HtmlService.createHtmlOutputFromFile("Sidebar");
    Logger.log("HTML file loaded successfully");
    Logger.log("HTML content length: " + html.getContent().length);
    return "Success: HTML file loaded. Length: " + html.getContent().length;
  } catch (e) {
    Logger.log("Error loading HTML: " + e.toString());
    return "Error: " + e.toString();
  }
}

/**
 * Gets the current spreadsheet URL and name.
 * Called from the sidebar to display spreadsheet info.
 */
function getSpreadsheetInfo() {
  try {
    var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    return {
      url: spreadsheet.getUrl(),
      name: spreadsheet.getName(),
    };
  } catch (e) {
    Logger.log("Error getting spreadsheet info: " + e.toString());
    return {
      url: "Unable to get URL",
      name: "Unknown",
    };
  }
}

/**
 * Main handler for chat messages coming from the sidebar.
 * Parses the API response and extracts messages and issues.
 */
function handleUserMessage(userMessage) {
  if (!userMessage) {
    return {
      reply: "Please type something for me to react to.",
      issues: null,
    };
  }

  try {
    // Get spreadsheet context
    var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    var activeSheet = spreadsheet.getActiveSheet();
    var spreadsheetUrl = spreadsheet.getUrl();
    var sheetTitle = activeSheet.getName();

    // Get or create session ID for this spreadsheet
    var sessionId = getOrCreateSessionId(spreadsheet.getId());

    // Make the API call
    var apiResponse = callChatApi(
      userMessage,
      spreadsheetUrl,
      sheetTitle,
      sessionId
    );

    // Parse the API response
    var parsed = parseApiResponse(apiResponse);

    // If issues were detected, highlight them with colors
    if (
      parsed.issues &&
      parsed.issues.potential_errors &&
      parsed.issues.potential_errors.length > 0
    ) {
      try {
        highlightIssues(parsed.issues.potential_errors);
      } catch (colorError) {
        Logger.log("Error highlighting issues: " + colorError.toString());
        // Don't fail the whole request if coloring fails
      }
    }

    return {
      reply: parsed.reply,
      issues: parsed.issues, // { potential_errors: [...] } or null
    };
  } catch (e) {
    Logger.log("Error in handleUserMessage: " + e.toString());
    return {
      reply: "Sorry, I encountered an error: " + e.toString(),
      issues: null,
    };
  }
}

/**
 * Parses the new API response format with messages array.
 * Extracts assistant messages for reply and tool messages for issues.
 */
function parseApiResponse(apiResponse) {
  var reply = "";
  var issues = null;

  if (!apiResponse || !apiResponse.messages) {
    return {
      reply: "No response received from the API.",
      issues: null,
    };
  }

  // Extract assistant messages for the reply
  var assistantMessages = [];
  var toolMessages = [];

  for (var i = 0; i < apiResponse.messages.length; i++) {
    var msg = apiResponse.messages[i];
    if (msg.role === "assistant" && msg.content) {
      assistantMessages.push(msg.content);
    } else if (
      msg.role === "tool" &&
      msg.metadata &&
      msg.metadata.payload &&
      msg.metadata.payload.potential_errors
    ) {
      toolMessages.push(msg.metadata.payload);
    }
  }

  // Combine assistant messages into reply
  if (assistantMessages.length > 0) {
    reply = assistantMessages.join("\n\n");
  } else {
    reply = "Analysis complete.";
  }

  // Extract issues from tool messages
  if (toolMessages.length > 0) {
    // Combine all potential_errors from all tool messages
    var allErrors = [];
    for (var j = 0; j < toolMessages.length; j++) {
      var payload = toolMessages[j];
      if (payload.potential_errors && Array.isArray(payload.potential_errors)) {
        allErrors = allErrors.concat(payload.potential_errors);
      }
    }

    if (allErrors.length > 0) {
      issues = {
        potential_errors: allErrors,
      };
    }
  }

  return {
    reply: reply,
    issues: issues,
  };
}

/**
 * Calls the real chat API endpoint.
 * @param {string} userMessage - The user's message
 * @param {string} spreadsheetUrl - The full URL of the spreadsheet
 * @param {string} sheetTitle - The name of the active sheet
 * @param {string} sessionId - Session ID for maintaining conversation context
 * @return {Object} The API response
 */
function callChatApi(userMessage, spreadsheetUrl, sheetTitle, sessionId) {
  var apiUrl = "https://fintech-hackathon-production.up.railway.app/chat";

  // Build the request payload
  var payload = {
    messages: [
      {
        id: generateMessageId(),
        role: "user",
        content: userMessage,
      },
    ],
    sheetContext: {
      spreadsheetId: spreadsheetUrl,
      sheetTitle: sheetTitle,
    },
    sessionId: sessionId,
  };

  // Set up request options
  var options = {
    method: "post",
    contentType: "application/json",
    headers: {
      "User-Agent": "insomnia/12.0.0",
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true, // Don't throw on HTTP errors, return response
  };

  // Make the API call
  var response = UrlFetchApp.fetch(apiUrl, options);
  var responseCode = response.getResponseCode();
  var responseText = response.getContentText();

  // Check for HTTP errors
  if (responseCode !== 200) {
    Logger.log(
      "API Error - Status: " + responseCode + ", Response: " + responseText
    );
    throw new Error(
      "API request failed with status " + responseCode + ": " + responseText
    );
  }

  // Parse JSON response
  try {
    return JSON.parse(responseText);
  } catch (e) {
    Logger.log("Error parsing API response: " + e.toString());
    throw new Error("Failed to parse API response: " + e.toString());
  }
}

/**
 * Gets or creates a session ID for the current spreadsheet.
 * Uses PropertiesService to persist session ID per spreadsheet.
 * @param {string} spreadsheetId - The spreadsheet ID
 * @return {string} The session ID
 */
function getOrCreateSessionId(spreadsheetId) {
  var properties = PropertiesService.getScriptProperties();
  var key = "sessionId_" + spreadsheetId;
  var sessionId = properties.getProperty(key);

  if (!sessionId) {
    // Generate a new session ID
    sessionId = "session_" + spreadsheetId + "_" + Date.now();
    properties.setProperty(key, sessionId);
  }

  return sessionId;
}

/**
 * Generates a unique message ID.
 * @return {string} A unique message ID
 */
function generateMessageId() {
  return "msg_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9);
}

/**
 * Highlights issues by calling the color endpoint.
 * @param {Array} issues - Array of issue objects with cell_location and color
 */
function highlightIssues(issues) {
  if (!issues || issues.length === 0) {
    return;
  }

  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  var spreadsheetId = spreadsheet.getId();

  // Build color payload from issues - only include issues with URL
  var colorPayload = [];

  for (var i = 0; i < issues.length; i++) {
    var issue = issues[i];
    if (issue.cell_location && issue.color && issue.url) {
      var colorItem = {
        cell_location: issue.cell_location,
        color: issue.color,
        message: issue.title || issue.message || "Issue detected",
        url: issue.url, // Only use issue URL, no fallback
      };
      colorPayload.push(colorItem);
    }
  }

  if (colorPayload.length === 0) {
    Logger.log("No issues with URL found to highlight");
    return;
  }

  // Call color endpoint - send requests grouped by URL
  var urlGroups = {};
  for (var j = 0; j < colorPayload.length; j++) {
    var item = colorPayload[j];
    if (!urlGroups[item.url]) {
      urlGroups[item.url] = [];
    }
    urlGroups[item.url].push(item);
  }

  // Store all responses
  var properties = PropertiesService.getScriptProperties();
  var allResponses = [];

  // Call API for each URL group
  for (var url in urlGroups) {
    var groupPayload = urlGroups[url];
    try {
      var colorResponse = callColorApi(groupPayload);

      if (colorResponse) {
        // Save the entire response
        allResponses.push(colorResponse);

        // Store response data for each cell location in this group
        for (var k = 0; k < groupPayload.length; k++) {
          var cellLoc = groupPayload[k].cell_location;
          var responseKey = "color_response_" + spreadsheetId + "_" + cellLoc;
          properties.setProperty(responseKey, JSON.stringify(colorResponse));

          // Also store snapshot_batch_id for backward compatibility
          if (colorResponse.snapshot_batch_id) {
            var snapshotKey = "snapshot_" + spreadsheetId + "_" + cellLoc;
            properties.setProperty(
              snapshotKey,
              colorResponse.snapshot_batch_id
            );
          }
        }

        Logger.log(
          "Highlighted " +
            groupPayload.length +
            " issue(s) for URL " +
            url +
            " with response: " +
            JSON.stringify(colorResponse)
        );
      }
    } catch (e) {
      Logger.log(
        "Error highlighting issues for URL " + url + ": " + e.toString()
      );
    }
  }
}

/**
 * Calls the color API endpoint to highlight cells.
 * @param {Array} colorPayload - Array of {cell_location, color, message} objects
 * @return {Object} API response with snapshot_batch_id
 */
function callColorApi(colorPayload) {
  var apiUrl =
    "https://fintech-hackathon-production.up.railway.app/tools/color";

  var options = {
    method: "post",
    contentType: "application/json",
    headers: {
      "User-Agent": "insomnia/12.0.0",
    },
    payload: JSON.stringify(colorPayload),
    muteHttpExceptions: true,
  };

  var response = UrlFetchApp.fetch(apiUrl, options);
  var responseCode = response.getResponseCode();
  var responseText = response.getContentText();

  if (responseCode !== 200) {
    Logger.log(
      "Color API Error - Status: " +
        responseCode +
        ", Response: " +
        responseText
    );
    throw new Error("Color API request failed with status " + responseCode);
  }

  try {
    return JSON.parse(responseText);
  } catch (e) {
    Logger.log("Error parsing color API response: " + e.toString());
    throw new Error("Failed to parse color API response");
  }
}

/**
 * Called when user clicks "Ignore" on an issue card.
 * Restores the original cell colors by calling the restore endpoint.
 * @param {string} cellLocation - The cell location (e.g., "A7", "3:6")
 * @return {Object} Success status
 */
function ignoreIssue(cellLocation) {
  Logger.log("Ignoring issue at %s (reverting colors)", cellLocation);

  try {
    var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    var spreadsheetId = spreadsheet.getId();
    var properties = PropertiesService.getScriptProperties();

    // Get the saved color response for this cell location
    var responseKey = "color_response_" + spreadsheetId + "_" + cellLocation;
    var responseJson = properties.getProperty(responseKey);

    var snapshotBatchId = null;

    if (responseJson) {
      try {
        var savedResponse = JSON.parse(responseJson);
        snapshotBatchId = savedResponse.snapshot_batch_id;
        Logger.log(
          "Found saved color response for " + cellLocation + ": " + responseJson
        );
      } catch (e) {
        Logger.log("Error parsing saved response: " + e.toString());
      }
    }

    // Fallback to old snapshot_batch_id storage
    if (!snapshotBatchId) {
      var snapshotKey = "snapshot_" + spreadsheetId + "_" + cellLocation;
      snapshotBatchId = properties.getProperty(snapshotKey);
    }

    if (!snapshotBatchId) {
      Logger.log(
        "No snapshot_batch_id found for cell location: " + cellLocation
      );
      return {
        success: false,
        error: "No snapshot found for this cell location",
      };
    }

    // Call restore endpoint to revert colors
    var restoreResponse = callRestoreApi(snapshotBatchId, [cellLocation]);

    if (restoreResponse && restoreResponse.status === "success") {
      // Remove the stored mappings
      properties.deleteProperty(responseKey);
      var snapshotKey = "snapshot_" + spreadsheetId + "_" + cellLocation;
      properties.deleteProperty(snapshotKey);

      Logger.log("Successfully restored colors for " + cellLocation);
      return {
        success: true,
        message: "Issue ignored, colors restored",
      };
    } else {
      Logger.log("Restore API returned non-success status");
      return {
        success: false,
        error: "Failed to restore colors",
      };
    }
  } catch (e) {
    Logger.log("Error ignoring issue: " + e.toString());
    return {
      success: false,
      error: e.toString(),
    };
  }
}

/**
 * Called when user clicks "Fix with AI" on an issue card.
 * Sends the issue to the AI to determine and apply fixes.
 * @param {Object} issueData - The full issue object with all metadata
 * @return {Object} Result with success, message, and snapshot_id for undo
 */
function fixIssueWithAI(issueData) {
  Logger.log("Fixing issue with AI: " + JSON.stringify(issueData));

  try {
    var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    var activeSheet = spreadsheet.getActiveSheet();
    var spreadsheetUrl = spreadsheet.getUrl();
    var sheetTitle = activeSheet.getName();
    var sessionId = getOrCreateSessionId(spreadsheet.getId());

    // Build a specific message for the AI about this issue
    var userMessage =
      "Fix this specific issue:\n\n" +
      "Location: " +
      issueData.cell_location +
      "\n" +
      "Severity: " +
      issueData.severity +
      "\n" +
      "Issue: " +
      issueData.title +
      "\n" +
      "Description: " +
      issueData.description +
      "\n";

    if (issueData.suggestedFix) {
      userMessage += "Suggested fix: " + issueData.suggestedFix + "\n";
    }

    userMessage +=
      "\nPlease use the update_cells tool to apply the appropriate fix for this issue.";

    // Call the chat API with the fix request
    var apiResponse = callChatApi(
      userMessage,
      spreadsheetUrl,
      sheetTitle,
      sessionId
    );

    // Parse the response to look for update_cells tool result
    var parsed = parseApiResponse(apiResponse);
    var updateCellsResult = extractUpdateCellsResult(apiResponse);

    if (updateCellsResult && updateCellsResult.snapshot_batch_id) {
      // Store the snapshot ID for undo
      var spreadsheetId = spreadsheet.getId();
      var properties = PropertiesService.getScriptProperties();
      var fixSnapshotKey =
        "fix_snapshot_" + spreadsheetId + "_" + issueData.cell_location;
      properties.setProperty(
        fixSnapshotKey,
        updateCellsResult.snapshot_batch_id
      );

      // Now revert the color highlight
      ignoreIssue(issueData.cell_location);

      Logger.log("AI fix applied successfully");
      return {
        success: true,
        message: parsed.reply || "Fix applied successfully",
        snapshot_id: updateCellsResult.snapshot_batch_id,
        cells_updated: updateCellsResult.count || 0,
      };
    } else {
      // AI responded but didn't use update_cells tool
      return {
        success: false,
        message:
          parsed.reply ||
          "AI couldn't determine how to fix this issue automatically",
      };
    }
  } catch (e) {
    Logger.log("Error fixing issue with AI: " + e.toString());
    return {
      success: false,
      error: e.toString(),
      message: "Error: " + e.toString(),
    };
  }
}

/**
 * Extract update_cells tool result from API response.
 * @param {Object} apiResponse - The API response with messages array
 * @return {Object|null} The update_cells result or null
 */
function extractUpdateCellsResult(apiResponse) {
  if (!apiResponse || !apiResponse.messages) {
    return null;
  }

  for (var i = 0; i < apiResponse.messages.length; i++) {
    var msg = apiResponse.messages[i];
    if (
      msg.role === "tool" &&
      msg.metadata &&
      msg.metadata.toolName === "update_cells" &&
      msg.metadata.payload
    ) {
      return msg.metadata.payload;
    }
  }

  return null;
}

/**
 * Undo AI-applied fixes for a specific cell location.
 * @param {string} cellLocation - The cell location to undo
 * @return {Object} Success status
 */
function undoAIFix(cellLocation) {
  Logger.log("Undoing AI fix for: " + cellLocation);

  try {
    var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    var spreadsheetId = spreadsheet.getId();
    var properties = PropertiesService.getScriptProperties();

    var fixSnapshotKey = "fix_snapshot_" + spreadsheetId + "_" + cellLocation;
    var snapshotBatchId = properties.getProperty(fixSnapshotKey);

    if (!snapshotBatchId) {
      return {
        success: false,
        error: "No undo snapshot found for this fix",
      };
    }

    // Call restore_cells endpoint
    var restoreResponse = callRestoreCellsApi(snapshotBatchId, [cellLocation]);

    if (restoreResponse && restoreResponse.status === "success") {
      // Remove the snapshot reference
      properties.deleteProperty(fixSnapshotKey);

      Logger.log("Successfully undid AI fix for " + cellLocation);
      return {
        success: true,
        message: "Fix undone successfully",
      };
    } else {
      return {
        success: false,
        error: "Failed to undo fix",
      };
    }
  } catch (e) {
    Logger.log("Error undoing AI fix: " + e.toString());
    return {
      success: false,
      error: e.toString(),
    };
  }
}

/**
 * Calls the restore API endpoint to restore cell colors.
 * @param {string} snapshotBatchId - The snapshot batch ID from the color endpoint
 * @param {Array} cellLocations - Array of cell locations to restore (optional, can be null to restore all)
 * @return {Object} API response
 */
function callRestoreApi(snapshotBatchId, cellLocations) {
  var apiUrl =
    "https://fintech-hackathon-production.up.railway.app/tools/restore";

  var payload = {
    snapshot_batch_id: snapshotBatchId,
  };

  // Only include cell_locations if provided
  if (cellLocations && cellLocations.length > 0) {
    payload.cell_locations = cellLocations;
  }

  var options = {
    method: "post",
    contentType: "application/json",
    headers: {
      "User-Agent": "insomnia/12.0.0",
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  };

  var response = UrlFetchApp.fetch(apiUrl, options);
  var responseCode = response.getResponseCode();
  var responseText = response.getContentText();

  if (responseCode !== 200) {
    Logger.log(
      "Restore API Error - Status: " +
        responseCode +
        ", Response: " +
        responseText
    );
    throw new Error("Restore API request failed with status " + responseCode);
  }

  try {
    return JSON.parse(responseText);
  } catch (e) {
    Logger.log("Error parsing restore API response: " + e.toString());
    throw new Error("Failed to parse restore API response");
  }
}

/**
 * Calls the restore_cells API endpoint to restore cell values after AI fixes.
 * @param {string} snapshotBatchId - The snapshot batch ID from update_cells
 * @param {Array} cellLocations - Array of cell locations to restore (optional)
 * @return {Object} API response
 */
function callRestoreCellsApi(snapshotBatchId, cellLocations) {
  var apiUrl =
    "https://fintech-hackathon-production.up.railway.app/tools/restore_cells";

  var payload = {
    snapshot_batch_id: snapshotBatchId,
  };

  if (cellLocations && cellLocations.length > 0) {
    payload.cell_locations = cellLocations;
  }

  var options = {
    method: "post",
    contentType: "application/json",
    headers: {
      "User-Agent": "insomnia/12.0.0",
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  };

  var response = UrlFetchApp.fetch(apiUrl, options);
  var responseCode = response.getResponseCode();
  var responseText = response.getContentText();

  if (responseCode !== 200) {
    Logger.log(
      "Restore Cells API Error - Status: " +
        responseCode +
        ", Response: " +
        responseText
    );
    throw new Error(
      "Restore cells API request failed with status " + responseCode
    );
  }

  try {
    return JSON.parse(responseText);
  } catch (e) {
    Logger.log("Error parsing restore cells API response: " + e.toString());
    throw new Error("Failed to parse restore cells API response");
  }
}
