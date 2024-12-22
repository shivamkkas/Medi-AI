
from fastapi import  Depends,APIRouter
from dotenv import load_dotenv
from ..schemas import DIET,SYMPTOM
from ..grpc_client import GRPCClient
from ..dependency import get_current_active_user
import os
import time
from google.protobuf.json_format import MessageToDict
load_dotenv()
port = os.getenv("PORT")
router = APIRouter(
     prefix = "/predict_medi",
     dependencies=[Depends(get_current_active_user)],
     responses={404:{"description":"Not found"}}
)
@router.post("/recommend_medi")
async def recommend(symptom: SYMPTOM):
     try: 
          command = GRPCClient(f"localhost:{port}")
          if symptom:
               response = command.run_symptom_prediction_client(symptom.symptom)
               # print("triggered",response)
               response_dict = MessageToDict(response)
               # print("mydict",response_dict)
               return {"Status":"Success","Data":response_dict}
          else:
               return {"Status":"Error","Data":"Symptom is required"}
     except Exception as e:
          return {"Status":"error","Error":e}     

@router.post("/get_diet_plan")
async def update(items: DIET):
     try:
          command = GRPCClient(f"localhost:{port}")
          if items:
               # items_dict = items.__dict__ if hasattr(items, 'dict') else dict(items)
               response = command.run_diet_plan_client(items)
          if response:
               my_dict = MessageToDict(response)
               return {"Status": "Success", "Data": my_dict}
          else:
               return {"Status": "Error", "Data": "No response received from service"}

     except Exception as e:
          return {"Status":"error","Error":e}      
     