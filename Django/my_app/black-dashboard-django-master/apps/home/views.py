
from django import template
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.contrib.auth.models import User
from django.template.loader import get_template
from .models import FoodItem
from django.template import TemplateDoesNotExist

template = get_template('home/user.html')


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('home') 
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})


@login_required
def user_profile(request):
    user = request.user
    
    if request.method == 'POST':
        # Update user profile information
        user.username = request.POST.get('username', user.username)
        user.email = request.POST.get('email', user.email)
        user.first_name = request.POST.get('full_name', user.first_name)
        user.save()
        messages.success(request, 'Profile updated successfully!')
        return render(request, 'home/user.html')
    
    return render(request, 'home/user.html')


from django.http import JsonResponse
from .models import FoodItem, RawMaterial

def create_food_item(request):
  if request.method == 'POST':
      
    food_item_name = request.POST.get('name')
    food_item = FoodItem.objects.create(name=food_item_name)

    # Access raw material data as lists of values submitted together
    raw_material_names = request.POST.getlist('raw_material_name[]')
    quantities = request.POST.getlist('quantity[]')
    quantity_types = request.POST.getlist('quantity_type[]')

    # Create RawMaterial objects for each entry in the lists
    for name, quantity, quantity_type in zip(raw_material_names, quantities, quantity_types):
      # Check if quantity is a valid number before creating the object
      try:
        quantity = float(quantity)  # Convert to a number (e.g., for calculations)
      except ValueError:
        quantity = None  # Handle invalid quantity input (optional)

      RawMaterial.objects.create(
          food_item=food_item,
          name=name,
          quantity=quantity,
          quantity_type=quantity_type
      )

    return render(request, 'home/raw_materials.html')  # Redirect to a success page after saving

  return render(request, 'home/raw_materials.html')



def fetch_food_items(request):
    food_items = FoodItem.objects.all()
    data = [{'name': food_item.name, 'raw_materials': [{'name': rm.name, 'quantity': rm.quantity, 'quantity_type': rm.quantity_type} for rm in food_item.rawmaterial_set.all()]} for food_item in food_items]
    return JsonResponse(data, safe=False)


def get_food_items():
    # Fetch food items from the database
    food_items = FoodItem.objects.all()
    return food_items

def render_page(request):
    # Fetch food items from the database
    food_items = FoodItem.objects.all()

    # Process any other data or perform any other operations here

    # Create a context dictionary with the data to pass to the template
    context = {
        'food_items': food_items,
        # Add any other data you want to pass to the template here
    }

    # Render the template with the provided context
    return render(request, 'path_to_your_template.html', context)




@login_required(login_url="/login/")
def index(request):
    context = {'segment': 'index'}

    html_template = loader.get_template('home/index.html')
    return HttpResponse(html_template.render(context, request))


@login_required(login_url="/login/")
def pages(request):
    context = {}
    # All resource paths end in .html.
    # Pick out the html file name from the url. And load that template.
    try:

        load_template = request.path.split('/')[-1]

        if load_template == 'admin':
            return HttpResponseRedirect(reverse('admin:index'))
        context['segment'] = load_template

        html_template = loader.get_template('home/' + load_template)
        return HttpResponse(html_template.render(context, request))

    except template.TemplateDoesNotExist:

        html_template = loader.get_template('home/page-404.html')
        return HttpResponse(html_template.render(context, request))

    except:
        html_template = loader.get_template('home/page-500.html')
        return HttpResponse(html_template.render(context, request))
 
    
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.urls import reverse

def upload_dataset(request):
    if request.method == 'POST' and request.FILES['dataset_file']:
        # Process the uploaded file here
        # Set upload_success to True after successful processing
        upload_success = True
        return HttpResponseRedirect(reverse('upload_success'))
    else:
        upload_success = False

    return render(request, 'upload_dataset.html', {'upload_success': upload_success})





from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.conf import settings
import os
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

# Assuming the RandomForest model is pre-trained and saved
def load_model():
    # Load the pre-trained model
    model_path = os.path.join(settings.BASE_DIR, 'model', 'random_forest_model.pkl')
    model = pd.read_pickle(model_path)
    return model

# This view handles the dataset upload and prediction
def upload_and_predict(request):
    if request.method == 'POST':
        # Handle file upload
        if 'dataset_file' in request.FILES:
            dataset_file = request.FILES['dataset_file']
            dataset = pd.read_csv(dataset_file)

            # Process dataset if necessary
            X = dataset.drop(columns=['Qty'])
            y = dataset['Qty']
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.4, random_state=60)

            # Load model and make predictions
            model = load_model()
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)

            # Store predictions to session or database if needed
            request.session['predictions'] = y_pred.tolist()

        # Handle direct prediction inputs
        day = request.POST.get('Day')
        month = request.POST.get('Month')
        year = request.POST.get('Year')
        temperature = request.POST.get('Temperature')
        precipitation = request.POST.get('Precipitation')
        special_occasion = request.POST.get('Special_Occasion')

        # Form a DataFrame for the input
        input_data = pd.DataFrame({
            'Day': [day],
            'Month': [month],
            'Year': [year],
            'Temperature': [temperature],
            'Precipitation': [precipitation],
            'Special Occasion': [special_occasion]
        })

        # Predict using the loaded model
        model = load_model()
        predicted_quantity = model.predict(input_data)[0]

        # Pass the prediction to the template
        return render(request, 'result.html', {
            'predicted_quantity': predicted_quantity
        })

    # If not POST or no file is uploaded, show the form
    return render(request, 'upload_dataset.html')

