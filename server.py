import grpc
from concurrent import futures
from src.grpc_services import diet_symptom_pb2
import src.grpc_services.diet_symptom_pb2_grpc as diet_symptom_pb2_grpc
import google.generativeai as genai
import os
import pandas as pd
import pickle
import numpy as np
from src.preprocess import SymptomQueryFilter,symptoms_dict,diseases_list
from dotenv import load_dotenv


load_dotenv()

# Load necessary data and models
sym_des = pd.read_csv("datasets/symtoms_df.csv")
precautions = pd.read_csv("datasets/precautions_df.csv")
workout = pd.read_csv("datasets/workout_df.csv")
description = pd.read_csv("datasets/description.csv")
medications = pd.read_csv('datasets/medications.csv')
diets = pd.read_csv("datasets/diets.csv")
svc = pickle.load(open('models/svc.pkl','rb'))

class DietPlanServicer(diet_symptom_pb2_grpc.DietPlanServiceServicer):
    def __init__(self):
        # Configure Gemini API
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel("models/gemini-pro")

    def GenerateDietPlan(self, request, context):
        prompt = f"""
        Can you suggest a comprehensive plan that includes diet and workout options for better fitness?
        for this user:
        dietary preferences: {request.dietary_preferences},
        fitness goals: {request.fitness_goals},
        lifestyle factors: {request.lifestyle_factors},
        dietary restrictions: {request.dietary_restrictions},
        health conditions: {request.health_conditions},
        user query: {request.user_query},

        Based on the above user's profile, create a customized plan that includes:

        Diet Recommendations: RETURN LIST
        5 specific diet types suited to their preferences and goals.

        Workout Options: RETURN LIST
        5 workout recommendations that align with their fitness level and goals.

        Meal Suggestions: RETURN LIST
        5 breakfast ideas.

        5 dinner options.

        Additional Recommendations: RETURN LIST
        Any useful snacks, supplements, or hydration tips tailored to their profile.
        """

        response = self.model.generate_content(prompt)
        
        # Parse response into gRPC response
        recommendations = {
            "diet_types": [],
            "workouts": [],
            "breakfasts": [],
            "dinners": [],
            "additional_tips": []
        }

        current_section = None
        for line in response.text.splitlines():
            if "Diet Recommendations:" in line:
                current_section = "diet_types"
            elif "Workout Options:" in line:
                current_section = "workouts"
            elif "Meal Suggestions:" in line:
                current_section = "breakfasts"
            elif "Dinner Options:" in line:
                current_section = "dinners"
            elif "Additional Recommendations:" in line:
                current_section = "additional_tips"
            else:
                if line.strip() and current_section:
                    recommendations[current_section].append(line.strip())

        return diet_symptom_pb2.DietPlanResponse(
            diet_types=recommendations['diet_types'],
            workouts=recommendations['workouts'],
            breakfasts=recommendations['breakfasts'],
            dinners=recommendations['dinners'],
            additional_tips=recommendations['additional_tips']
        )

def helper(dis):
    desc = description[description['Disease'] == dis]['Description']
    desc = " ".join([w for w in desc])

    pre = precautions[precautions['Disease'] == dis][['Precaution_1', 'Precaution_2', 'Precaution_3', 'Precaution_4']]
    pre = [col for col in pre.values]

    med = medications[medications['Disease'] == dis]['Medication']
    med = [med for med in med.values]

    die = diets[diets['Disease'] == dis]['Diet']
    die = [die for die in die.values]

    wrkout = workout[workout['disease'] == dis]['workout']

    return desc, pre, med, die, wrkout

class SymptomPredictionServicer(diet_symptom_pb2_grpc.SymptomPredictionServiceServicer):
    def __init__(self):
        self.symptom_filter = SymptomQueryFilter('datasets/Symptom-severity.csv')

    def get_predicted_value(self, patient_symptoms):
        input_vector = np.zeros(len(symptoms_dict))
        for item in patient_symptoms:
            if item in symptoms_dict:
                input_vector[symptoms_dict[item]] = 1
        return diseases_list[svc.predict([input_vector])[0]]

    def PredictDisease(self, request, context):
        try:
            # Filter and analyze symptoms
            filtered_symptoms = self.symptom_filter.filter_query(request.symptoms)
            
            valid_symptoms = filtered_symptoms['valid_symptoms']
            precision_metrics = filtered_symptoms['precision_metrics']
            if not valid_symptoms:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("No recognizable symptoms detected.")
                return diet_symptom_pb2.DiseaseResponse()
            # Handle low precision symptoms
            if precision_metrics['precision_score'] < 5:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(f"Low symptom precision (Score: {precision_metrics['precision_score']}%). "
                                       "Consider providing more specific or additional symptoms.")
                return diet_symptom_pb2.DiseaseResponse()
            # Predict disease
            predicted_disease = self.get_predicted_value(valid_symptoms)
            
            # Fetch additional disease details
            dis_des, precautions, medications_list, rec_diet, workout_list = helper(predicted_disease)
            
            # Prepare precautions list
            my_precautions = list(precautions[0]) if precautions else []
            return diet_symptom_pb2.DiseaseResponse(
                predicted_disease=predicted_disease,
                disease_description=dis_des,
                precautions=my_precautions,
                medications=medications_list,
                recommended_diet=rec_diet,
                recommended_workout=list(workout_list),
                precision_score=int(precision_metrics['precision_score'])
            )
        
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error processing symptoms: {str(e)}")
            return diet_symptom_pb2.DiseaseResponse()

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    diet_symptom_pb2_grpc.add_DietPlanServiceServicer_to_server(DietPlanServicer(), server)
    diet_symptom_pb2_grpc.add_SymptomPredictionServiceServicer_to_server(SymptomPredictionServicer(), server)
    server.add_insecure_port('[::]:7051')
    print("Starting gRPC server on port 7051...")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()