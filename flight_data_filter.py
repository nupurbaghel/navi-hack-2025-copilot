import pandas as pd
from pathlib import Path


class FlightDataFilter:
    """
    Filter flight data CSV to remove pre-flight rows and keep only operational flight data.
    """
    
    def __init__(self, input_csv_path):
        """
        Initialize the filter with input CSV path.
        
        Args:
            input_csv_path (str): Path to the input CSV file
        """
        self.input_path = Path(input_csv_path)
        self.df = None
        self.filtered_df = None
        
    def load_data(self):
        """Load the CSV file into a pandas DataFrame."""
        # Read CSV, skipping the first comment line
        self.df = pd.read_csv(self.input_path, skiprows=2)
        print(f"Loaded {len(self.df)} rows from {self.input_path.name}")
        return self
    
    def filter_preflight(self, rpm_threshold=500, speed_threshold=1):
        """
        Filter out pre-flight data based on engine and movement indicators.
        
        Args:
            rpm_threshold (int): Minimum RPM to consider engine operational (default: 500)
            speed_threshold (float): Minimum ground speed in knots (default: 1)
        
        Returns:
            self: For method chaining
        """
        if self.df is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        # Convert numeric columns, handling empty strings
        self.df[' E1 RPM'] = pd.to_numeric(self.df[' E1 RPM'], errors='coerce').fillna(0)
        self.df[' GndSpd'] = pd.to_numeric(self.df[' GndSpd'], errors='coerce').fillna(0)
        self.df[' E1 FFlow'] = pd.to_numeric(self.df[' E1 FFlow'], errors='coerce').fillna(0)
        self.df['    IAS'] = pd.to_numeric(self.df['    IAS'], errors='coerce').fillna(0)
        
        # Filter condition: Engine running AND (fuel flowing OR aircraft moving)
        condition = (
            (self.df[' E1 RPM'] >= rpm_threshold) &
            ((self.df[' E1 FFlow'] > 0) | (self.df[' GndSpd'] >= speed_threshold))
        )
        
        self.filtered_df = self.df[condition].copy()
        
        rows_removed = len(self.df) - len(self.filtered_df)
        print(f"Filtered out {rows_removed} pre-flight rows")
        print(f"Remaining flight data: {len(self.filtered_df)} rows")
        
        return self
    
    def filter_engine_running(self, rpm_threshold=100):
        """
        Simple filter: Keep only rows where engine is running.
        
        Args:
            rpm_threshold (int): Minimum RPM (default: 100)
        
        Returns:
            self: For method chaining
        """
        if self.df is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        self.df[' E1 RPM'] = pd.to_numeric(self.df[' E1 RPM'], errors='coerce').fillna(0)
        self.filtered_df = self.df[self.df[' E1 RPM'] >= rpm_threshold].copy()
        
        rows_removed = len(self.df) - len(self.filtered_df)
        print(f"Filtered out {rows_removed} rows with RPM < {rpm_threshold}")
        print(f"Remaining data: {len(self.filtered_df)} rows")
        
        return self
    
    def filter_in_flight(self, altitude_threshold=100, speed_threshold=40):
        """
        Filter to keep only in-flight data (airborne).
        
        Args:
            altitude_threshold (int): Minimum altitude MSL in feet (default: 100)
            speed_threshold (int): Minimum airspeed in knots (default: 40)
        
        Returns:
            self: For method chaining
        """
        if self.df is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        self.df['  AltMSL'] = pd.to_numeric(self.df['  AltMSL'], errors='coerce').fillna(0)
        self.df['    IAS'] = pd.to_numeric(self.df['    IAS'], errors='coerce').fillna(0)
        
        condition = (
            (self.df['  AltMSL'] >= altitude_threshold) &
            (self.df['    IAS'] >= speed_threshold)
        )
        
        self.filtered_df = self.df[condition].copy()
        
        rows_removed = len(self.df) - len(self.filtered_df)
        print(f"Filtered to in-flight data only")
        print(f"Removed {rows_removed} ground/taxi rows")
        print(f"In-flight data: {len(self.filtered_df)} rows")
        
        return self
    
    def filter_preflight_only(self):
        """
        Filter to keep only pre-flight data (where AltInd is empty or 0).
        
        Returns:
            self: For method chaining
        """
        if self.df is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        # Convert AltInd column to numeric, handling empty strings
        self.df['  AltInd'] = pd.to_numeric(self.df['  AltInd'], errors='coerce').fillna(0)
        
        # Filter condition: AltInd is 0 or NaN (preflight stage)
        condition = (self.df['  AltInd'] == 0)
        
        self.filtered_df = self.df[condition].copy()
        
        rows_removed = len(self.df) - len(self.filtered_df)
        print(f"Filtered to pre-flight data only")
        print(f"Removed {rows_removed} in-flight/taxi rows")
        print(f"Pre-flight data: {len(self.filtered_df)} rows")
        
        return self
    
    def get_filtered_data(self):
        """
        Get the filtered DataFrame.
        
        Returns:
            pd.DataFrame: Filtered data
        """
        if self.filtered_df is None:
            raise ValueError("No filtered data available. Run a filter method first.")
        return self.filtered_df
    
    def save_to_csv(self, output_path=None):
        """
        Save filtered data to CSV file.
        
        Args:
            output_path (str, optional): Output file path. If None, adds '_filtered' suffix to input name.
        
        Returns:
            str: Path to the output file
        """
        if self.filtered_df is None:
            raise ValueError("No filtered data available. Run a filter method first.")
        
        if output_path is None:
            output_path = self.input_path.parent / f"{self.input_path.stem}_filtered.csv"
        else:
            output_path = Path(output_path)
        
        self.filtered_df.to_csv(output_path, index=False)
        print(f"Saved filtered data to: {output_path}")
        
        return str(output_path)
    
    def get_summary(self):
        """
        Get summary statistics of the filtered data.
        
        Returns:
            dict: Summary information
        """
        if self.filtered_df is None:
            raise ValueError("No filtered data available. Run a filter method first.")
        
        summary = {
            'total_rows': len(self.filtered_df),
            'start_time': self.filtered_df[' Lcl Time'].iloc[0] if ' Lcl Time' in self.filtered_df.columns else 'N/A',
            'end_time': self.filtered_df[' Lcl Time'].iloc[-1] if ' Lcl Time' in self.filtered_df.columns else 'N/A',
            'max_altitude': self.filtered_df['  AltMSL'].max() if '  AltMSL' in self.filtered_df.columns else 'N/A',
            'max_speed': self.filtered_df[' GndSpd'].max() if ' GndSpd' in self.filtered_df.columns else 'N/A',
            'max_rpm': self.filtered_df[' E1 RPM'].max() if ' E1 RPM' in self.filtered_df.columns else 'N/A',
        }
        
        return summary
    
    def print_summary(self):
        """Print summary statistics."""
        summary = self.get_summary()
        print("\n=== FLIGHT DATA SUMMARY ===")
        print(f"Total rows: {summary['total_rows']}")
        print(f"Start time: {summary['start_time']}")
        print(f"End time: {summary['end_time']}")
        print(f"Max altitude: {summary['max_altitude']} ft MSL")
        print(f"Max ground speed: {summary['max_speed']} kts")
        print(f"Max RPM: {summary['max_rpm']}")
        print("===========================\n")


# Example usage
if __name__ == "__main__":
    # Filter for pre-flight data only (AltInd is empty or 0)
    preflight_filter = FlightDataFilter("navi-hack-2025-copilot/Cirrus KHAF-KSQL 05_05_2024/log_240505_132633_KHAF.csv")
    preflight_filter.load_data().filter_preflight_only().print_summary()
    preflight_filter.save_to_csv("navi-hack-2025-copilot/preflight_data/preflight_data_only.csv")
