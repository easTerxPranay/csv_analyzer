import pandas as pd
import plotly.express as px
from flask import Flask, render_template, request, redirect, url_for, session
import io
import os
import uuid

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here' # **CHANGE THIS FOR PRODUCTION**

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            return redirect(request.url)
        
        file = request.files['csv_file']
        
        if file.filename == '':
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            try:
                unique_filename = str(uuid.uuid4()) + '.csv'
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                
                file.save(filepath)
                
                session['uploaded_filepath'] = filepath
                session['original_filename'] = file.filename
                
                return redirect(url_for('analyze'))
            except Exception as e:
                return render_template('index.html', error=f"Error saving file: {e}. Please try again.")
    
    return render_template('index.html', error=None)

@app.route('/analyze', methods=['GET', 'POST'])
def analyze():
    filepath = session.get('uploaded_filepath')
    original_filename = session.get('original_filename', 'your_data.csv')

    if not filepath or not os.path.exists(filepath):
        return redirect(url_for('index')) 

    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        return render_template('index.html', error=f"Error reading CSV from temp file: {e}. Please re-upload.")

    head_html = df.head().to_html(classes='data-table', border=0)
    desc_html = df.describe().to_html(classes='data-table', border=0)
    
    # Categorize columns by data type for better selection in HTML
    columns = df.columns.tolist()
    numerical_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
    
    plot_html = ""
    plot_error = ""

    if request.method == 'POST':
        x_col = request.form.get('x_column')
        y_col = request.form.get('y_column')
        color_col = request.form.get('color_column') # For adding 'color' dimension
        plot_type = request.form.get('plot_type')

        # Default plot options
        plot_params = {}
        if x_col and x_col != 'None':
            plot_params['x'] = x_col
        if y_col and y_col != 'None':
            plot_params['y'] = y_col
        if color_col and color_col != 'None':
            plot_params['color'] = color_col
        
        try:
            fig = None
            if plot_type == 'scatter':
                if x_col in numerical_cols and y_col in numerical_cols:
                    fig = px.scatter(df, **plot_params, title=f'Scatter Plot: {x_col} vs {y_col}')
                else:
                    plot_error = "Scatter plot requires two numerical columns for X and Y axes."
            
            elif plot_type == 'bar':
                if x_col and y_col and x_col in columns and y_col in numerical_cols: # X can be categorical, Y must be numerical
                    fig = px.bar(df, **plot_params, title=f'Bar Chart: {y_col} by {x_col}')
                else:
                    plot_error = "Bar chart requires a numerical column for Y-axis and any column for X-axis."

            elif plot_type == 'line':
                # Line plots often imply sequential data; for simplicity, we'll allow two numerical or one categorical, one numerical
                if x_col in columns and y_col in numerical_cols:
                    fig = px.line(df, **plot_params, title=f'Line Plot: {y_col} over {x_col}')
                else:
                    plot_error = "Line plot requires a numerical column for Y-axis and any column for X-axis."
            
            elif plot_type == 'histogram':
                if x_col and x_col in numerical_cols: # Histogram needs one numerical column
                    fig = px.histogram(df, x=x_col, **plot_params, title=f'Histogram of {x_col}')
                else:
                    plot_error = "Histogram requires one numerical column."
            
            elif plot_type == 'box_plot':
                if y_col and y_col in numerical_cols: # Box plot needs one numerical column for y
                    fig = px.box(df, y=y_col, x=x_col if x_col and x_col != 'None' else None, **plot_params, title=f'Box Plot of {y_col}')
                else:
                    plot_error = "Box plot requires at least one numerical column for Y-axis."
            
            elif plot_type == 'pie_chart':
                if x_col and y_col and x_col in categorical_cols and y_col in numerical_cols: # X for names, Y for values
                    fig = px.pie(df, names=x_col, values=y_col, title=f'Pie Chart of {y_col} by {x_col}')
                else:
                    plot_error = "Pie chart requires one categorical column for 'names' and one numerical column for 'values'."

            else:
                plot_error = "Invalid plot type selected."
                fig = None

            if fig:
                plot_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
            elif not plot_error: # If fig is None but no specific error was set, provide a general error
                 plot_error = "Could not generate plot with selected options. Check column types and selections."

        except Exception as e:
            plot_error = f"An unexpected error occurred while generating plot: {e}"

    return render_template('analyze.html', 
                           filename=original_filename,
                           head_data=head_html, 
                           desc_data=desc_html, 
                           columns=columns, # All columns for x/y
                           numerical_columns=numerical_cols, # Numerical only for histogram/box plot Y
                           categorical_columns=categorical_cols, # Categorical only for pie names
                           plot_html=plot_html,
                           plot_error=plot_error)

import os # Add this import at the top if not already there

# ... (rest of your app.py code) ...

if __name__ == '__main__':
    # Replit uses the PORT environment variable. If not found, default to 5000.
    # Host 0.0.0.0 is needed for Replit to be accessible externally.
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
    # You can set debug=False for a production-like environment,
    # but for a hackathon demo, debug=True is often fine.