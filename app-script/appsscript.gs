{
  "timeZone": "Europe/Berlin",
  "exceptionLogging": "STACKDRIVER",
  "runtimeVersion": "V8",
  "addOns": {
    "common": {
      "name": "Sheet Mangler",
      "logoUrl": "https://fintech-hackathon-production.up.railway.app/mangler.png",
      "layoutProperties": {
        "primaryColor": "#0F9D58",
        "secondaryColor": "#F1F3F4"
      }
    },
    "sheets": {
      "homepageTrigger": {
        "runFunction": "showCopilotSidebar",
        "enabled": true
      }
    }
  }
}