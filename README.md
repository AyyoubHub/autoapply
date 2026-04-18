# 🧠 JOBENIUM

**JOBENIUM** is an automated job application tool built in Python that interacts with major French job platforms — **APEC**, **HelloWork**, and **JobTeaser**.  
It automates the login, search, and application process, saving you time when applying to multiple offers.

## ⚙️ Features

- Automatic login and job application on multiple platforms  
- Custom email, passwords, and messages stored securely in `config.json`  
- Logs all actions in `logs/history.log`  
- CLI interface for choosing which platform to run  
- Uses `undetected-chromedriver` to avoid bot detection

## 🧩 Prerequisites

Before running JOBENIUM, make sure you have:

- **Python 3.9+**
- **Google Chrome** installed  

If the script does not run, **change the Chrome version** in the code:
```python
driver = uc.Chrome(version_main=140, options=options)
```
→ Replace 140 with your local Chrome’s main version (e.g., 141, 142, etc.).

To find your Chrome version:

On Chrome, go to chrome://settings/help

## 🛠 Installation

1. Clone the repository:
```bash
git clone https://github.com/hamzaaitbourhim/jobenium.git
cd jobenium
```

2. Install dependencies manually:
```bash
pip install selenium
pip install undetected-chromedriver
pip install questionary
```

3. Configure credentials:
- Edit configs/config.json with your email, passwords...

## 🧾 Account Requirements

Before using JOBENIUM, make sure you already have **active accounts** on the platforms you plan to use.

⚠️ **Important:**  
Your accounts must be created using a **regular email and password**.  
Logins via **Google**, **LinkedIn**, or **Facebook** are **not supported**, because the automation scripts require direct access to the login form.

Make sure your profile is well set up and your CV is uploaded on each platform before running the script.

## 🚀 Usage
To launch the program:
```python
python scripts/launcher.py
```

## 📜 Logs
All activities (login attempts, applied jobs, errors) are recorded in:
```bash
logs/history.log
```
You can check this file to monitor sessions or debug issues.

## 🤝 Contributing
Contributions are welcome! To contribute:
1. Fork this repository.
2. Create a branch for your feature (`git checkout -b feature-name`).
3. Commit your changes (`git commit -m "Add a new feature"`).
4. Push to your branch (`git push origin feature-name`).
5. Create a pull request.

## ⚠️ Disclaimer

This project is for educational purposes only.
Automating applications on job platforms may violate their terms of use — use responsibly.