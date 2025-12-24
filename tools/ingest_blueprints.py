import json
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.cipher_service import CipherService
from app.database_factory import get_db_interface

# Define components separately to avoid massive nesting syntax errors
single_column_components = [
  { "id": "root-column", "component": { "Column": { "children": { "explicitList": ["title-heading", "item-list"] } } } },
  { "id": "title-heading", "component": { "Text": { "usageHint": "h1", "text": { "path": "title" } } } },
  { "id": "item-list", "component": { "List": { "direction": "vertical", "children": { "template": { "componentId": "item-card-template", "dataBinding": "/items" } } } } },
  { "id": "item-card-template", "component": { "Card": { "child": "card-layout" } } },
  { "id": "card-layout", "component": { "Row": { "children": { "explicitList": ["template-image", "card-details"] } } } },
  { "id": "template-image", "weight": 1, "component": { "Image": { "url": { "path": "imageUrl" } } } },
  { "id": "card-details", "weight": 2, "component": { "Column": { "children": { "explicitList": ["template-name", "template-rating", "template-detail", "template-link", "template-book-button"] } } } },
  { "id": "template-name", "component": { "Text": { "usageHint": "h3", "text": { "path": "name" } } } },
  { "id": "template-rating", "component": { "Text": { "text": { "path": "rating" } } } },
  { "id": "template-detail", "component": { "Text": { "text": { "path": "detail" } } } },
  { "id": "template-link", "component": { "Text": { "text": { "path": "infoLink" } } } },
  { 
      "id": "template-book-button", 
      "component": { 
          "Button": { 
              "child": "book-now-text", 
              "primary": True, 
              "action": { 
                  "name": "book_restaurant", 
                  "context": [ 
                      { "key": "restaurantName", "value": { "path": "name" } }, 
                      { "key": "imageUrl", "value": { "path": "imageUrl" } }, 
                      { "key": "address", "value": { "path": "address" } } 
                  ] 
              } 
          } 
      } 
  },
  { "id": "book-now-text", "component": { "Text": { "text": { "literalString": "Book Now" } } } }
]

booking_form_components = [
  { "id": "booking-form-column", "component": { "Column": { "children": { "explicitList": ["booking-title", "restaurant-image", "restaurant-address", "party-size-field", "datetime-field", "dietary-field", "submit-button"] } } } },
  { "id": "booking-title", "component": { "Text": { "usageHint": "h2", "text": { "path": "title" } } } },
  { "id": "restaurant-image", "component": { "Image": { "url": { "path": "imageUrl" } } } },
  { "id": "restaurant-address", "component": { "Text": { "text": { "path": "address" } } } },
  { "id": "party-size-field", "component": { "TextField": { "label": { "literalString": "Party Size" }, "text": { "path": "partySize" }, "type": "number" } } },
  { "id": "datetime-field", "component": { "DateTimeInput": { "label": { "literalString": "Date & Time" }, "value": { "path": "reservationTime" }, "enableDate": True, "enableTime": True } } },
  { "id": "dietary-field", "component": { "TextField": { "label": { "literalString": "Dietary Requirements" }, "text": { "path": "dietary" } } } },
  { 
      "id": "submit-button", 
      "component": { 
          "Button": { 
              "child": "submit-reservation-text", 
              "action": { 
                  "name": "submit_booking", 
                  "context": [ 
                      { "key": "restaurantName", "value": { "path": "restaurantName" } }, 
                      { "key": "partySize", "value": { "path": "partySize" } }, 
                      { "key": "reservationTime", "value": { "path": "reservationTime" } }, 
                      { "key": "dietary", "value": { "path": "dietary" } }, 
                      { "key": "imageUrl", "value": { "path": "imageUrl" } } 
                  ] 
              } 
          } 
      } 
  },
  { "id": "submit-reservation-text", "component": { "Text": { "text": { "literalString": "Submit Reservation" } } } }
]

BLUEPRINTS = [
    {
        "name": "SINGLE_COLUMN_LIST_EXAMPLE",
        "description": "A list of restaurant cards with a single column layout.",
        "payload": [
          { "beginRendering": { "surfaceId": "default", "root": "root-column", "styles": { "primaryColor": "#FF0000", "font": "Roboto" } } },
          { "surfaceUpdate": {
            "surfaceId": "default",
            "components": single_column_components
          } },
          { "dataModelUpdate": {
            "surfaceId": "default",
            "path": "/",
            "contents": [
              { "key": "items", "valueMap": [
                { "key": "item1", "valueMap": [
                  { "key": "name", "valueString": "The Fancy Place" },
                  { "key": "rating", "valueNumber": 4.8 },
                  { "key": "detail", "valueString": "Fine dining experience" },
                  { "key": "infoLink", "valueString": "https://example.com/fancy" },
                  { "key": "imageUrl", "valueString": "https://example.com/fancy.jpg" },
                  { "key": "address", "valueString": "123 Main St" }
                ] },
                { "key": "item2", "valueMap": [
                  { "key": "name", "valueString": "Quick Bites" },
                  { "key": "rating", "valueNumber": 4.2 },
                  { "key": "detail", "valueString": "Casual and fast" },
                  { "key": "infoLink", "valueString": "https://example.com/quick" },
                  { "key": "imageUrl", "valueString": "https://example.com/quick.jpg" },
                  { "key": "address", "valueString": "456 Oak Ave" }
                ] }
              ] }
            ]
          } }
        ]
    },
    {
        "name": "BOOKING_FORM_EXAMPLE",
        "description": "A form for booking a restaurant table.",
        "payload": [
          { "beginRendering": { "surfaceId": "booking-form", "root": "booking-form-column", "styles": { "primaryColor": "#FF0000", "font": "Roboto" } } },
          { "surfaceUpdate": {
            "surfaceId": "booking-form",
            "components": booking_form_components
          } },
          { "dataModelUpdate": {
            "surfaceId": "booking-form",
            "path": "/",
            "contents": [
              { "key": "title", "valueString": "Book a Table at [RestaurantName]" },
              { "key": "address", "valueString": "[Restaurant Address]" },
              { "key": "restaurantName", "valueString": "[RestaurantName]" },
              { "key": "partySize", "valueString": "2" },
              { "key": "reservationTime", "valueString": "" },
              { "key": "dietary", "valueString": "" },
              { "key": "imageUrl", "valueString": "" }
            ]
          } }
        ]
    }
]

def ingest_blueprints():
    print("Initializing Database Interface...")
    db = get_db_interface()
    
    for bp in BLUEPRINTS:
        name = bp["name"]
        print(f"Processing blueprint: {name}")
        try:
            # Store in Cipher Memory
            mid = db.add_memory(
                category="blueprint", 
                content={
                    "name": name, 
                    "description": bp["description"],
                    "a2ui_payload": bp["payload"]
                }
            )
            print(f"Stored blueprint {name} with ID: {mid}")
            
        except Exception as e:
            print(f"Error storing blueprint {name}: {e}")

if __name__ == "__main__":
    ingest_blueprints()
