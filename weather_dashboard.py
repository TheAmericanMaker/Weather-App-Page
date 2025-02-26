import sys
import json
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLineEdit, QPushButton, QLabel, 
                            QStackedWidget, QComboBox, QFrame, QScrollArea)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
import requests
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import logging
from urllib.parse import quote

class WeatherDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        self.setWindowTitle("Weather Dashboard")
        self.setMinimumSize(1000, 800)
        
        # Initialize variables
        self.current_unit = 'C'
        self.last_weather_data = None
        self.load_favorites()
        
        # Setup UI
        self.setup_ui()
        
        self.dark_mode = False
        self.apply_theme()

    def load_favorites(self):
        try:
            with open('favorites.json', 'r') as f:
                self.favorites = json.load(f)
        except FileNotFoundError:
            self.favorites = []

    def save_favorites(self):
        with open('favorites.json', 'w') as f:
            json.dump(self.favorites, f)

    def update_favorites_display(self):
        self.favorites_combo.clear()
        for favorite in self.favorites:
            self.favorites_combo.addItem(favorite['name'])

    def toggle_unit(self, unit):
        self.current_unit = unit
        if unit == 'C':
            self.celsius_btn.setChecked(True)
            self.fahrenheit_btn.setChecked(False)
        else:
            self.celsius_btn.setChecked(False)
            self.fahrenheit_btn.setChecked(True)
        
        if self.last_weather_data:
            self.display_weather(self.last_weather_data)

    def search_location(self):
        query = self.search_input.text()
        if not query:
            self.show_error("Please enter a location")
            return
            
        try:
            # Add User-Agent header as required by Nominatim's terms of use
            headers = {
                'User-Agent': 'WeatherDashboard/1.0',
                'Accept': 'application/json'
            }
            
            # URL encode the query
            encoded_query = requests.utils.quote(query)
            geocoding_url = f"https://nominatim.openstreetmap.org/search?q={encoded_query}&format=json&limit=1"
            
            self.logger.debug(f"Requesting: {geocoding_url}")
            response = requests.get(geocoding_url, headers=headers)
            
            # Check if the request was successful
            response.raise_for_status()
            
            # Check if we got any data
            data = response.json()
            if not data:
                self.show_error("Location not found")
                return
                
            location = data[0]
            self.logger.debug(f"Found location: {location}")
            
            # Get weather for the location
            self.get_weather(
                float(location['lat']), 
                float(location['lon']), 
                location['display_name']
            )
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error: {str(e)}")
            self.show_error(f"Network error: {str(e)}")
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON response: {str(e)}")
            self.show_error("Invalid response from server")
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            self.show_error(f"Error: {str(e)}")

    def get_weather(self, lat, lon, location_name):
        try:
            # Add parameters to make the URL more reliable
            url = (f"https://www.7timer.info/bin/api.pl?"
                  f"lon={lon:.4f}&lat={lat:.4f}"
                  f"&product=civil&output=json")
            
            self.logger.debug(f"Requesting weather: {url}")
            response = requests.get(url)
            response.raise_for_status()
            
            weather_data = response.json()
            if not weather_data:
                self.show_error("No weather data available")
                return
                
            self.logger.debug("Weather data received successfully")
            
            # Add location to favorites
            self.add_to_favorites({
                'name': location_name,
                'lat': lat,
                'lon': lon
            })
            
            self.display_weather(weather_data)
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Weather API error: {str(e)}")
            self.show_error(f"Weather API error: {str(e)}")
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid weather data: {str(e)}")
            self.show_error("Invalid weather data received")
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            self.show_error(f"Error: {str(e)}")

    def display_weather(self, data):
        """Display weather information"""
        self.last_weather_data = data
        self.logger.debug(f"Received weather data: {data}")
        
        # Clear previous weather display
        for i in reversed(range(self.weather_layout.count())): 
            self.weather_layout.itemAt(i).widget().setParent(None)
        
        try:
            # Get current time
            current_time = datetime.now()
            
            # Find the forecast closest to current time
            current_hour = current_time.hour
            forecasts = data['dataseries']
            closest_forecast_idx = 0
            smallest_diff = float('inf')
            
            for idx, forecast in enumerate(forecasts):
                hour_diff = abs(forecast['timepoint'] - current_hour)
                if hour_diff < smallest_diff:
                    smallest_diff = hour_diff
                    closest_forecast_idx = idx
            
            # Display forecasts starting from the closest time
            for forecast in forecasts[closest_forecast_idx:closest_forecast_idx + 4]:  # Show 4 forecasts
                self.logger.debug(f"Forecast data: {forecast}")
                temp = self.convert_temp(forecast['temp2m'])
                
                # Calculate forecast time by adding hours
                forecast_time = current_time + timedelta(hours=forecast['timepoint'])
                time_str = forecast_time.strftime("%A, %B %d at %I:%M %p")
                
                weather_info = f"""
                    <div style='font-family: "Segoe UI", Arial, sans-serif;'>
                        <div style='font-size: 16px; font-weight: bold; color: #1A365D; margin-bottom: 8px;'>
                            {time_str}
                        </div>
                        <div style='font-size: 24px; margin-bottom: 8px; color: #03074d;'>
                            {temp}°{self.current_unit}
                        </div>
                        <div style='font-size: 14px; margin-bottom: 4px;'>
                            <span style='color: #03074d; font-weight: bold;'>Weather:</span> <span style='color: #03074d;'>{forecast['weather']}</span>
                        </div>
                        <div style='font-size: 14px; margin-bottom: 4px;'>
                            <span style='color: #03074d; font-weight: bold;'>Wind:</span> <span style='color: #03074d;'>{self.get_wind_description(forecast['wind10m']['speed'])}</span>
                        </div>
                        <div style='font-size: 14px; margin-bottom: 4px;'>
                            <span style='color: #03074d; font-weight: bold;'>Direction:</span> <span style='color: #03074d;'>{self.get_wind_direction(forecast['wind10m']['direction'])}</span>
                        </div>
                        <div style='font-size: 14px;'>
                            <span style='color: #03074d; font-weight: bold;'>Humidity:</span> <span style='color: #03074d;'>{forecast['rh2m']}</span>
                        </div>
                    </div>
                """
                
                weather_label = QLabel(weather_info)
                weather_label.setTextFormat(Qt.TextFormat.RichText)
                weather_label.setStyleSheet("""
                    QLabel {
                        background-color: #6970fa;
                        border: 4px solid #03074d;
                        border-radius: 12px;
                        padding: 16px;
                        margin: 8px;
                    }
                    QLabel:hover {
                        border-color: #4299E1;
                    }
                """)
                self.weather_layout.addWidget(weather_label)
            
            # Update charts
            self.update_charts(data)
            
        except Exception as e:
            self.logger.error(f"Error displaying weather: {str(e)}")
            self.logger.exception("Detailed error information:")
            self.show_error(f"Error displaying weather: {str(e)}")

    def update_charts(self, data):
        self.figure.clear()
        
        # Get the same range of data as displayed in the forecast cards
        current_hour = datetime.now().hour
        closest_forecast_idx = min(range(len(data['dataseries'])), 
                                 key=lambda i: abs(data['dataseries'][i]['timepoint'] - current_hour))
        display_data = data['dataseries'][closest_forecast_idx:closest_forecast_idx + 4]
        
        # Temperature chart
        ax1 = self.figure.add_subplot(211)
        times = range(len(display_data))
        temps = [self.convert_temp(d['temp2m']) for d in display_data]
        ax1.plot(times, temps, 'b-', linewidth=2, marker='o')
        ax1.set_title('Temperature Trend', pad=10)
        ax1.set_ylabel(f'Temperature (°{self.current_unit})')
        ax1.grid(True)
        
        # Wind speed chart
        ax2 = self.figure.add_subplot(212)
        winds = [d['wind10m']['speed'] for d in display_data]
        ax2.bar(times, winds, color='skyblue')
        ax2.set_title('Wind Speed', pad=10)
        ax2.set_ylabel('Wind Speed (Beaufort)')
        ax2.grid(True)
        
        # Adjust layout to prevent overlapping
        self.figure.tight_layout(pad=3.0)
        
        self.canvas.draw()

    def convert_temp(self, temp):
        if self.current_unit == 'F':
            return round((temp * 9/5) + 32)
        return temp

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()

    def apply_theme(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QMainWindow { background-color: #1a202c; color: #e2e8f0; }
                QLabel { color: #e2e8f0; }
                QPushButton { 
                    background-color: #4299e1; 
                    color: white; 
                    border: none; 
                    padding: 5px 10px; 
                    border-radius: 5px; 
                }
                QLineEdit { 
                    background-color: #2d3748; 
                    color: #e2e8f0; 
                    border: 1px solid #4299e1; 
                    padding: 5px; 
                    border-radius: 5px; 
                }
            """)
        else:
            self.setStyleSheet("")

    def show_error(self, message):
        """Display error message in the weather display area"""
        self.logger.error(message)
        error_label = QLabel(f"❌ {message}")
        error_label.setStyleSheet("""
            color: #dc2626;
            background-color: #fee2e2;
            padding: 10px;
            border-radius: 5px;
            margin: 5px;
        """)
        self.weather_layout.addWidget(error_label)
        
        # Remove the error message after 5 seconds
        QTimer.singleShot(5000, lambda: error_label.setParent(None))

    def load_favorite_location(self, location_name):
        """Load weather data for a selected favorite location"""
        if not location_name:
            return
            
        selected_location = next(
            (loc for loc in self.favorites if loc['name'] == location_name), 
            None
        )
        
        if selected_location:
            self.get_weather(
                selected_location['lat'],
                selected_location['lon'],
                selected_location['name']
            )

    def add_to_favorites(self, location):
        """Add a location to favorites if it's not already there"""
        if not any(f['name'] == location['name'] for f in self.favorites):
            self.favorites.append(location)
            self.save_favorites()
            self.update_favorites_display()

    def get_wind_description(self, beaufort_scale):
        """Convert Beaufort scale number to description"""
        descriptions = {
            0: 'Calm (0-1 km/h)',
            1: 'Light air (1-5 km/h)',
            2: 'Light breeze (6-11 km/h)',
            3: 'Gentle breeze (12-19 km/h)',
            4: 'Moderate breeze (20-28 km/h)',
            5: 'Fresh breeze (29-38 km/h)',
            6: 'Strong breeze (39-49 km/h)',
            7: 'High wind (50-61 km/h)',
            8: 'Gale (62-74 km/h)',
            9: 'Strong gale (75-88 km/h)',
            10: 'Storm (89-102 km/h)',
            11: 'Violent storm (103-117 km/h)',
            12: 'Hurricane force (118+ km/h)'
        }
        return descriptions.get(beaufort_scale, 'Unknown')

    def get_wind_direction(self, direction):
        # Handle cardinal directions directly
        direction_map = {
            'N': 'North',
            'NNE': 'North-Northeast',
            'NE': 'Northeast',
            'ENE': 'East-Northeast',
            'E': 'East',
            'ESE': 'East-Southeast',
            'SE': 'Southeast',
            'SSE': 'South-Southeast',
            'S': 'South',
            'SSW': 'South-Southwest',
            'SW': 'Southwest',
            'WSW': 'West-Southwest',
            'W': 'West',
            'WNW': 'West-Northwest',
            'NW': 'Northwest',
            'NNW': 'North-Northwest'
        }
        
        return direction_map.get(direction, 'Unknown')

    def setup_ui(self):
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Create search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter city name...")
        search_button = QPushButton("Search")
        search_button.clicked.connect(self.search_location)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_button)
        layout.addLayout(search_layout)
        
        # Temperature unit toggle
        unit_layout = QHBoxLayout()
        self.celsius_btn = QPushButton("°C")
        self.fahrenheit_btn = QPushButton("°F")
        self.celsius_btn.setCheckable(True)
        self.fahrenheit_btn.setCheckable(True)
        self.celsius_btn.setChecked(True)
        self.celsius_btn.clicked.connect(lambda: self.toggle_unit('C'))
        self.fahrenheit_btn.clicked.connect(lambda: self.toggle_unit('F'))
        unit_layout.addWidget(self.celsius_btn)
        unit_layout.addWidget(self.fahrenheit_btn)
        layout.addLayout(unit_layout)
        
        # Create scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        # Weather display area
        self.weather_display = QFrame()
        self.weather_layout = QVBoxLayout(self.weather_display)
        content_layout.addWidget(self.weather_display)
        
        # Charts container
        charts_container = QWidget()
        charts_layout = QVBoxLayout(charts_container)
        self.figure = Figure(figsize=(8, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(400)  # Set minimum height for the canvas
        charts_layout.addWidget(self.canvas)
        content_layout.addWidget(charts_container)
        
        # Add spacing between weather display and charts
        content_layout.addSpacing(20)
        
        # Set the content widget to the scroll area
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # Favorites section
        favorites_layout = QHBoxLayout()
        self.favorites_combo = QComboBox()
        self.favorites_combo.currentTextChanged.connect(self.load_favorite_location)
        favorites_layout.addWidget(QLabel("Favorites:"))
        favorites_layout.addWidget(self.favorites_combo)
        layout.addLayout(favorites_layout)
        
        # Load favorites
        self.update_favorites_display()
        
        # Theme toggle
        theme_button = QPushButton("Toggle Theme")
        theme_button.clicked.connect(self.toggle_theme)
        layout.addWidget(theme_button)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = WeatherDashboard()
    window.show()
    sys.exit(app.exec()) 