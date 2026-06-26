import os
import glob
import json
import time
import requests
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
from PIL import Image, ImageTk
from google import genai

# --- CONFIGURATION ---
CONFIG_FILE = 'config.json'

class CardScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pokémon Card AI Scanner")
        self.root.geometry("900x600")
        
        # State variables
        self.running = False
        self.client = None
        self.pokemon_api_key = None
        
        # Build the UI components
        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        """Creates the GUI layout."""
        # --- Top Frame: Controls ---
        top_frame = tk.Frame(self.root, pady=10, padx=10)
        top_frame.pack(side=tk.TOP, fill=tk.X)

        tk.Label(top_frame, text="Image Folder:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        
        # FIX 1: Grab the absolute current working directory
        current_dir = os.getcwd()
        self.path_var = tk.StringVar(value=current_dir) 
        self.path_entry = tk.Entry(top_frame, textvariable=self.path_var, width=40)
        self.path_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Button(top_frame, text="Browse...", command=self.browse_folder).pack(side=tk.LEFT, padx=5)
        
        # FIX 2: Standard macOS buttons (no bg/fg color overrides)
        self.start_btn = tk.Button(top_frame, text="Start Processing", command=self.start_processing)
        self.start_btn.pack(side=tk.LEFT, padx=15)
        
        self.stop_btn = tk.Button(top_frame, text="Stop", state=tk.DISABLED, command=self.stop_processing)
        self.stop_btn.pack(side=tk.LEFT)

        # --- Middle Frame: Image Preview and Text Log ---
        mid_frame = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        mid_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Left Side: Image Preview
        self.image_label = tk.Label(mid_frame, text="No Image", bg="gray", width=40)
        mid_frame.add(self.image_label, minsize=300)

        # Right Side: Text Log
        self.log_area = scrolledtext.ScrolledText(mid_frame, wrap=tk.WORD, font=("Consolas", 10))
        mid_frame.add(self.log_area, minsize=400)

        # --- Bottom Frame: Status Bar ---
        bottom_frame = tk.Frame(self.root, relief=tk.SUNKEN, bd=1)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(bottom_frame, textvariable=self.status_var, anchor=tk.W, padx=10, font=("Arial", 10)).pack(fill=tk.X)

    def load_config(self):
        """Loads API keys from config.json"""
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                
            gemini_key = config.get("GEMINI_API_KEY")
            self.pokemon_api_key = config.get("POKEMON_API_KEY")

            if not gemini_key or not self.pokemon_api_key:
                self.log("[!] Missing API keys in config.json. Please provide both.")
            else:
                self.client = genai.Client(api_key=gemini_key)
                self.log("[*] Configuration loaded successfully. Ready to scan.")
                
        except FileNotFoundError:
            self.log(f"[!] Configuration file '{CONFIG_FILE}' not found.")
        except json.JSONDecodeError:
            self.log(f"[!] Error parsing '{CONFIG_FILE}'. Ensure it is valid JSON.")

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.path_var.set(folder_selected)

    def log(self, message):
        """Thread-safe method to append text to the scrolled text widget."""
        self.root.after(0, self._log_safe, message)

    def _log_safe(self, message):
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)

    def update_status(self, text):
        """Thread-safe method to update the bottom status bar."""
        self.root.after(0, lambda: self.status_var.set(text))

    def update_image(self, image_path):
        """Thread-safe method to load and scale the active image."""
        self.root.after(0, self._update_image_safe, image_path)

    def _update_image_safe(self, image_path):
        try:
            img = Image.open(image_path)
            # Resize image to fit nicely in the UI while maintaining aspect ratio
            img.thumbnail((300, 450)) 
            self.photo = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.photo, text="")
        except Exception as e:
            self.image_label.config(image='', text="Image Load Error")
            self.log(f"[!] Could not render image preview: {e}")

    def start_processing(self):
        if not self.client:
            messagebox.showerror("Error", "API keys not loaded. Check config.json.")
            return
            
        target_dir = self.path_var.get()
        # Find all JPGs in the target directory
        search_path = os.path.join(target_dir, "*.jpg")
        self.image_files = glob.glob(search_path)

        if not self.image_files:
            messagebox.showinfo("Not Found", f"No .jpg files found in '{target_dir}'.")
            return

        # Update UI state
        self.running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.path_entry.config(state=tk.DISABLED)
        
        self.log("\n" + "="*50)
        self.log(f"Found {len(self.image_files)} image(s). Starting background job...")

        # Launch the background thread
        threading.Thread(target=self.process_queue, daemon=True).start()

    def stop_processing(self):
        """Signals the background thread to halt."""
        self.running = False
        self.log("\n[!] Stop requested. Halting after current operation...")
        self.update_status("Stopping...")
        self.stop_btn.config(state=tk.DISABLED)

    def finish_processing(self):
        """Resets the UI state when the thread completes or is stopped."""
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.path_entry.config(state=tk.NORMAL)
        self.update_status("Ready")
        self.log("="*50 + "\nProcessing Complete!")

    # --- BACKGROUND THREAD LOGIC ---

    def process_queue(self):
        """The main loop that runs off the main GUI thread."""
        total = len(self.image_files)
        
        for index, image_path in enumerate(self.image_files, start=1):
            if not self.running:
                break
                
            self.update_status(f"Processing {index} / {total}")
            self.update_image(image_path)
            
            filename = os.path.basename(image_path)
            self.log(f"\n--- Processing: {filename} ---")
            
            # Step 1: Vision AI
            extracted_name, extracted_number = self.scan_card_with_gemini(image_path)
            
            # Step 2: Query Pokemon API
            if extracted_name and self.running:
                self.fetch_api_details_native(extracted_name, extracted_number)
                
            # Step 3: Rate Limiting
            if index < total and self.running:
                self.log("\n  [zZz] Pacing requests... waiting 9 seconds...")
                # Sleep in 1-second chunks so we can interrupt it instantly if the user clicks Stop
                for _ in range(9):
                    if not self.running:
                        break
                    time.sleep(1)
                    
        # Reset UI on completion
        self.root.after(0, self.finish_processing)

    def scan_card_with_gemini(self, image_path):
        """Uploads the image to Gemini 2.5 Flash using the modern SDK."""
        self.log("  [1/3] Uploading to Gemini...")
        try:
            sample_file = self.client.files.upload(file=image_path)
        except Exception as e:
            self.log(f"  [!] Failed to upload image: {e}")
            return None, None
            
        if not self.running: return None, None
        
        prompt = """
        Examine this Pokémon card. Find the name of the Pokémon and the specific card number. 
        The number is usually at the bottom (e.g., '58', '23', '96', or a promo code like 'AR6'). 
        Ignore the set total (the number after the slash).
        
        Respond ONLY with a valid JSON object in this exact format, with no markdown formatting:
        {"name": "Card Name", "number": "Card Number"}
        """
        
        self.log("  [2/3] Analyzing image...")
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[sample_file, prompt]
            )
            raw_json = response.text.replace('```json', '').replace('```', '').strip()
            card_data = json.loads(raw_json)
            
            name = card_data.get('name')
            number = card_data.get('number')
            self.log(f"      -> AI Found: '{name}' | Number: '{number}'")
            return name, number
            
        except Exception as e:
            self.log(f"  [!] Failed to process Gemini response: {e}")
            return None, None

    def fetch_api_details_native(self, name, number):
        """Queries the Pokemon TCG API and extracts prices for ALL conditions."""
        query_parts = []
        first_word = name.split()[0]
        query_parts.append(f'name:"{first_word}*"')
        
        if number:
            query_parts.append(f'number:{number}')
            
        query_string = ' '.join(query_parts)
        self.log(f"  [3/3] Querying Pokémon API for: {query_string}")
        
        # 1. Provide the clean, base URL with no query parameters attached
        url = "https://api.pokemontcg.io/v2/cards"
        headers = {"X-Api-Key": self.pokemon_api_key}
        
        # 2. Pass the query string as a dictionary so requests safely encodes it
        payload = {"q": query_string}
        
        try:
            # 3. Add the params argument to the GET request
            response = requests.get(url, headers=headers, params=payload)
            response.raise_for_status()
 
            data = response.json()
            cards = data.get('data', [])
            
            if not cards:
                self.log("      -> No API match found.")
                return
                
            card = cards[0]
            self.log("  [+] API Match Found!")
            self.log(f"      Official Name: {card.get('name')}")
            
            set_data = card.get('set', {})
            self.log(f"      Set:         {set_data.get('name')} (Released: {set_data.get('releaseDate')})")
            self.log(f"      Rarity:      {card.get('rarity', 'N/A')}")
            
            # --- Extract all conditions ---
            tcgplayer = card.get('tcgplayer', {})
            prices = tcgplayer.get('prices', {})
            
            if prices:
                self.log("      --- Market Prices by Edition ---")
                
                # Loop through every finish/printing provided by the API
                for finish, price_data in prices.items():
                    
                    # Clean up the API keys to look nice and readable
                    clean_name = finish.replace('1stEdition', '1st Edition ')
                    clean_name = clean_name.replace('reverseHolofoil', 'Reverse Holo')
                    clean_name = clean_name.replace('holofoil', 'Holo')
                    clean_name = clean_name.replace('normal', 'Non-Holo')
                    clean_name = clean_name.strip().title()
                    
                    market = price_data.get('market', 'N/A')
                    low = price_data.get('low', 'N/A')
                    high = price_data.get('high', 'N/A')
                    
                    self.log(f"        • {clean_name}: ${market} (Low: ${low} | High: ${high})")
            else:
                self.log("      Market Price: No TCGPlayer data available")                   
 
        except Exception as e:
            self.log(f"  [!] API Request failed: {e}")

if __name__ == "__main__":
    # Create the main window and start the application
    root = tk.Tk()
    app = CardScannerApp(root)
    root.mainloop()
