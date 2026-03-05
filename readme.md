## Credit Wise
CreditWise is a full stack application that recommends the best credit card for a transaction. 

### Architecture
React Frontend -> FastAPI Backend -> Recommendation Logic

### API Endpoints

#### Health Check
GET /health
Response:
{"ok": true}

#### Recommend Credit Card
POST  /recommend
Example Request:
{ 
    "amount": 50, 
    "category": "dining", 
    "channel": "Online" 
}
Example response:
{
  "best_card": "card 1",
  "reason": "3x cashback on dining"
}

### Tech Stack
Backend:
Python
FastAPI
Pydantic
Uvicorn

Frontend:
React
TypeScript
Vite
