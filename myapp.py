from flask import Flask, render_template, request, jsonify,session, redirect, url_for,make_response,send_file,flash
import os
import requests
from functools import wraps
import secrets
import csv
# Generate a random secret key
secret_key = secrets.token_hex(16) 
app = Flask(__name__)

app.secret_key = secret_key
def read_symptoms():
    symptoms = []
    try:
        # Use an absolute path or relative to the script's location
        csv_path = os.path.join(os.path.dirname(__file__), 'datasets/Symptom-severity.csv')
        
        with open(csv_path, mode='r') as file:
            csv_reader = csv.reader(file)
            next(csv_reader)  # Skip header
            for row in csv_reader:
                name, weight = row
                symptoms.append({
                    'name': name,
                    'weight': int(weight.strip())
                })
    except Exception as e:
        print(f"Error reading CSV: {e}")
    
    return symptoms
@app.route('/')
def home():
    user_data = request.args.get('user_data', session.get('user_data'))
    if user_data:
        return render_template('index.html', user_data=user_data)
    return render_template('index.html',)

@app.route('/login', methods=['POST','GET'])
def login():
    if request.method == 'POST':
        try:
            # Get JSON data from the request
            data = request.get_json()
            print(data)
            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                return jsonify({
                    "status": "error",
                    "message": "Username and password are required"
                }), 400

            # Prepare login data
            login_url = "http://127.0.0.1:8000/api/users/user/login"
            login_data = {
                "grant_type": "password",
                "username": username,
                "password": password,
                "scope": "",
                "client_id": "string",
                "client_secret": "string"
            }

            # Set headers for the API request
            headers = {"accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}

            # Make the login request
            response = requests.post(login_url,data=login_data,headers=headers)

            if response.status_code == 200:
                print("hello")
                token = response.json().get("access_token")
                
                # Make the protected request
                protected_url = "http://127.0.0.1:8000/api/users/user/me"
                auth_headers = {
                    "accept": "application/json",
                    "Authorization": f"Bearer {token}"
                }
                session['access_token'] = token
                protected_response = requests.get(protected_url, headers=auth_headers)

                if protected_response.status_code == 200:
                    resp = jsonify({
                    "status": "success",
                    "token": token,
                })
                    return resp
                else:
                    return jsonify({
                        "status": "error",
                        "message": "Failed to fetch user data"
                    }), protected_response.status_code

            else:
                error_message = "Login failed"
                try:
                    error_data = response.json()
                    error_message = error_data.get('detail', error_message)
                except:
                    pass

                return jsonify({
                    "status": "error",
                    "message": error_message
                }), response.status_code

        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"An error occurred: {str(e)}"
            }), 500
    return render_template("login.html")    

@app.route('/signup', methods=['POST'])
def signup():
    try:
        # Get JSON data from request
        data = request.get_json()
        
        # Extract required fields
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        # Validate required fields
        if not all([username, email, password]):
            return jsonify({
                "status": "error",
                "message": "Username, email, and password are required"
            }), 400
        
        # Basic validation
        if len(password) < 8:
            return jsonify({
                "status": "error",
                "message": "Password must be at least 8 characters long"
            }), 400
        
        # Prepare signup data for the API
        signup_url = "http://127.0.0.1:8000/api/users/user/signup"
        signup_data = {
            "username": username,
            "email": email,
            "password": password
        }
        
        # Set headers for the API request
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Make the signup request
        response = requests.post(
            signup_url,
            json=signup_data,
            headers=headers
        )
        
        # Handle API response
        if response.status_code == 200 or response.status_code == 201:
            return jsonify({
                "status": "success",
                "message": "Account created successfully",
                "data": response.json()
            })
        else:
            # Try to get detailed error message from API
            error_message = "Registration failed"
            try:
                error_data = response.json()
                if isinstance(error_data, dict):
                    error_message = error_data.get('detail', error_message)
                elif isinstance(error_data, list) and error_data:
                    error_message = error_data[0].get('msg', error_message)
            except:
                pass
            
            return jsonify({
                "status": "error",
                "message": error_message
            }), response.status_code
            
    except requests.RequestException as e:
        # Handle network or connection errors
        return jsonify({
            "status": "error",
            "message": f"Connection error: {str(e)}"
        }), 500
        
    except Exception as e:
        # Handle any other unexpected errors
        return jsonify({
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}"
        }), 500
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = session.get('access_token')  # Get token from session
        if not token:
            return redirect(url_for('login'))  # Redirect to login if no token
        return f(token, *args, **kwargs)
    return decorated

@app.route('/userprofile', methods=['GET'])
@token_required
def get_user_profile(token):
    try:
        # API endpoint for getting user data
        protected_url = "http://127.0.0.1:8000/api/users/user/me"
        
        # Set up headers with the token
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        # Make request to the protected endpoint
        response = requests.get(protected_url, headers=headers)
        
        # Check if request was successful
        if response.status_code == 200:
            user_data = response.json()
            session['user_data'] = user_data
            return render_template('userprofile.html', user_data=user_data)
        
        # Handle different error cases
        elif response.status_code == 401:
            return render_template('userprofile.html', error_message="Unauthorized access. Please login again.")
            
        elif response.status_code == 403:
            return render_template('userprofile.html', error_message="Forbidden access.")
            
        else:
            return render_template(
                'userprofile.html', 
                error_message="Failed to fetch user data", 
                error_details=response.text
            )
            
    except requests.RequestException as e:
        return render_template(
            'userprofile.html', 
            error_message="Failed to connect to authentication server", 
            error_details=str(e)
        )
        
    except Exception as e:
       return render_template(
            'userprofile.html', 
            error_message="An unexpected error occurred", 
            error_details=str(e)
        )
    # return render_template('main.html') 
@app.route("/GetDiet", methods=['POST', 'GET'])
@token_required
def getdiet(token):
    if request.method == 'POST':
        # Get token from session
        # token = session.get('access_token')
        if not token:
            # Handle case where user is not authenticated
            return redirect(url_for('login'))
    
        try:
            # API endpoint
            api_url = "http://127.0.0.1:8000/api/functions/predict_medi/get_diet_plan"
            
            # Set up headers with token
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Get data from form or request body
            data = request.get_json() if request.is_json else request.form.to_dict()
            print("your request",data)
            req ={
            "dietary_preferences": data['dietaryPreferences'],
            "fitness_goals": data['fitnessGoals'],
            "lifestyle_factors": data['lifestyleFactors'],
            "dietary_restrictions": data['dietaryRestrictions'],
            "health_conditions": data['healthConditions'],
            "user_query": data['query']}

            # Make API request
            response = requests.post(api_url, 
                                     json=req,
                                     headers=headers)
            

            # Check if request was successful
            if response.status_code == 200:
                recommendations = response.json()
                print("your data",recommendations)
                return jsonify({
                "status": "success",
                "message": "Get recommendation successfully",
                "data": recommendations['Data']
            })
            else:
                # Handle API errors
                return jsonify({
                    "error": "Failed to fetch diet recommendations",
                    "status": response.status_code
                }), response.status_code
                
        except requests.RequestException as e:
            # Handle request errors
            return jsonify({
                "error": "API request failed",
                "details": str(e)
            }), 500
    # GET request - just render the template
    user_data = request.args.get('user_data', session.get('user_data'))
    return render_template("diet.html", user_data=user_data,info={})
@app.route("/GetMedicine",methods=['POST', 'GET'])
@token_required
def getMedi(token):
    if request.method == 'POST':
        # token = session.get('access_token')

        if not token:
            # Handle case where user is not authenticated
            return redirect(url_for('login'))
        try:
            # API endpoint
            api_url = "http://127.0.0.1:8000/api/functions/predict_medi/recommend_medi"
            
            # Set up headers with token
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Get data from form or request body
            data = request.get_json() if request.is_json else request.form.to_dict()
            print("your data",data)
            req={"symptom": data['symptoms']}
            response = requests.post(api_url, 
                                     json=req,
                                     headers=headers)
            print("your response",response.json())
            if response.status_code == 200:
                info = response.json()
                result = info['Data']
                print("your data",result)
                session['diet_preference'] = result
                user_data = request.args.get('user_data', session.get('user_data'))
                return render_template("medi.html",user_data=user_data,predicted_disease=result['predictedDisease'], 
                                       dis_des=result['diseaseDescription'],
                                       my_precautions= result['precautions'], 
                                       medications=result['medications'], 
                                       my_diet=result['recommendedDiet'],
                                       workout=result['recommendedWorkout'],
                                       precision_score=int(result['precisionScore']),
                                       input_symptoms=req['symptom'])
            else:
                # Handle API errors
                return render_template("medi.html",jsonify({
                    "error": "Failed to fetch diet recommendations",
                    "status": response.status_code
                }), response.status_code)
                
        except requests.RequestException as e:
            # Handle request errors
            return jsonify({
                "error": "API request failed",
                "details": str(e)
            }), 500
            

    user_data = request.args.get('user_data', session.get('user_data'))
    return render_template("medi.html",user_data=user_data)
@app.route("/contactus")
def contactus():
    user_data = request.args.get('user_data', session.get('user_data'))
    return render_template("contact.html",user_data=user_data)

@app.route("/profile",methods=['PUT','GET','POST'])
@token_required
def update_user(token):
    if request.method == 'POST':

        # token = session.get('access_token')

        if not token:
            # Handle case where user is not authenticated
            return redirect(url_for('login'))
        try:
            # API endpoint
            api_url = "http://127.0.0.1:8000/api/users/user/profile"
            
            # Set up headers with token
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Get data from form or request body
            data = request.get_json() if request.is_json else request.form.to_dict()
            print("your data",data)
            req={
                "full_name": data['full_name'],
                "age": data['age'],
                "bio": data['bio'],
                "health_conditions": data['health_conditions']
                }
            response = requests.put(api_url, 
                                     json=req,
                                     headers=headers)
            print("your response",response.json())
            if response.status_code == 200:
                info = response.json()
                print("your data",info)
                user_data = request.args.get('user_data', session.get('user_data'))
                return render_template("users.html",user_data=user_data,res = info)
            else:
                # Handle API errors
                info = jsonify({
                    "message": "Failed to update user",
                    "status": response.status_code
                })
                return render_template("users.html",user_data=user_data,res = info)
                
        except requests.RequestException as e:
            # Handle request errorsres =
            info = jsonify({
                "message": "API request failed",
                "details": str(e)
            })
            return render_template("users.html",user_data=user_data,res = info)
            
    user_data = request.args.get('user_data', session.get('user_data'))
    return render_template("users.html",user_data=user_data)

@app.route('/logout')
def logout():
    # Clear user session
    session.clear()

    # Add a flash message to notify the user
    flash("You have been successfully logged out.", "success")

    # Redirect to the home or login page
    return redirect(url_for('login'))
@app.route('/disease')
def symptom_list():
    symptoms = read_symptoms()
    return render_template('data.html', symptoms=symptoms)
@app.route('/download_pdf')
def download():
    if 'user_data' not in session:
        return "You must be logged in to download data.", 401

    user_data = session['user_data']
    username = user_data.get('username', 'unknown_user')
    diet_preference = user_data.get('diet_preference', 'Not specified')

    # Create file content
    file_content = f"Username: {username}\nDiet Preference: {diet_preference}\n"

    # Create a temporary file
    filename = f"{username}_diet_plan.txt"
    filepath = os.path.join(os.getcwd(), filename)

    with open(filepath, 'w') as f:
        f.write(file_content)

    # Serve the file for download
    response = make_response(send_file(filepath, as_attachment=True))
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"

    # Clean up after sending the file
    os.remove(filepath)

    return response

if __name__ == '__main__':
    app.run(debug=True)