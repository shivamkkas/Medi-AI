import sys
import os
import time

# Full path to package1 directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import grpc
import src.grpc_services.diet_symptom_pb2 as diet_symptom_pb2
import src.grpc_services.diet_symptom_pb2_grpc as diet_symptom_pb2_grpc

class GRPCClient:
     def __init__(self, server_address):
        self.channel = grpc.insecure_channel(server_address)
     def run_diet_plan_client(self,req):
          stub = diet_symptom_pb2_grpc.DietPlanServiceStub(self.channel)
          req = req.__dict__
          request = diet_symptom_pb2.DietPlanRequest(
               dietary_preferences=req['dietary_preferences'],
               fitness_goals=req['fitness_goals'],
               lifestyle_factors=req['lifestyle_factors'],
               dietary_restrictions=req['dietary_restrictions'],
               health_conditions=req['health_conditions'],
               user_query=req['user_query']
          )
          try:
               response = stub.GenerateDietPlan(request)
               return response
          except grpc.RpcError as e:
               print(f"RPC failed: {e}")

     def run_symptom_prediction_client(self,symptoms):
          stub = diet_symptom_pb2_grpc.SymptomPredictionServiceStub(self.channel)
          # print(symptoms,self.channel)
          request = diet_symptom_pb2.SymptomRequest(
               symptoms=symptoms
          )
          
          try:
               response = stub.PredictDisease(request)
               return response
          except grpc.RpcError as e:
               print(f"RPC failed: {e}")  
# if __name__=="__main__":
#      co = GRPCClient(f"localhost:7051") 
#      res={
#      "dietary_preferences": "vegetarian",
#      "fitness_goals": "weight loss",
#      "lifestyle_factors": "active",
#      "dietary_restrictions": "gluten-free",
#      "health_conditions": "Neutral",
#      "user_query": "Dont prescribe home additional protein"
#      }
#      res = co.run_diet_plan_client(res)      
#      print(res)