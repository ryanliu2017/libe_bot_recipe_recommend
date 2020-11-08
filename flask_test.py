from flask import Flask,render_template,request

app=Flask(__name__,template_folder=".")
@app.route('/kafka_consumer',methods=['POST','GET'])
def kafka():
    print(request.values)
    if request.values:
        print(request.values)
        user_id = request.values.get("user_id")
        ingredient_name = request.values.get("food_name")
        quantity = request.values.get("food_weight")
        print(f"user_id: {user_id}")
        print(f"ingredient: {ingredient_name}, {quantity}")
        return f"{user_id}, you have successfully post data to server."
    else:
        return "Please visit the url with data"

if __name__ == '__main__':
    app.run(host='0.0.0.0',port='5000',debug=True)