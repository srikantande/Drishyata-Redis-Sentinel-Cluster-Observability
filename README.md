# 🚀 Drishyata Redis Sentinel Cluster Observability Monitor

A **Live, Auto-Refreshing Dashboard** built with Streamlit and Redis-Py for monitoring the health, performance, and key metrics of multiple Redis clusters managed by Sentinel.

This tool provides immediate visibility into the state of your Redis infrastructure.

---

## ✨ Key Features

### Live Dashboard (`Live Monitor` View)

* **Always Visible Key Metrics:** Core metrics—**Master Health**, **Keys (Master)**, **Used Memory (Master)**, and **Slaves Count**—are displayed as high-visibility cards for immediate assessment.
* **Toggleable Node Details:** The detailed table view showing **Keys**, **Clients**, and **Memory** for every individual master and slave node is kept clean inside a collapsible expander.
* **Sentinel Health Status:** Dedicated section detailing the health, tilt status, and masters monitored by the Sentinel network.
* **Auto-Refresh:** The dashboard automatically updates based on the interval set in `config.ini`.

### Historical View (`History Viewer` View)

* **Snapshot Logging:** Continuously logs health, key counts, clients, and memory usage for all nodes into a local SQLite database.
* **Data Export:** Allows users to filter and download full historical data as a CSV file.

---

## 🛠️ Getting Started

### 📦 1. Prerequisites & Installation

You need Python (>= 3.10.12) and a running Redis Sentinel setup.

1.  **Install Python Packages:**

    ```
    $ mkdir /opt/Drishyata
    copy main.py, logo.png, config.ini, & requirements.txt
    $ cd /opt/Drishyata
    $ pip install -r requirements.txt

    ```

2.  **Save the Script:**
    Save the application code as `main.py` (or any other `.py` file).

### ⚙️ 2. Configuration (`config.ini`)

The application requires a configuration file named `config.ini` to be placed in the **same directory** as the main Python script.

This file defines which Sentinels to connect to and how often to refresh the data.

### 🚀 3. Execution

```
nohup streamlit run /opt/Drishyata/main.py --server.port 14567 --server.fileWatcherType=none &
```
###   4. You can now view your Streamlit app in your browser.

  Local URL: http://localhost:14567
  
  Network URL: http://<internal_ip>:14567
  
  External URL: http://<external_ip>:14567

## 👨‍💻 Contributing and Licensing
This software is an open-source project. Contributions, bug reports, and feature suggestions are welcome!

### 🔒 Copyright and Contact
© Drishyata 2025. All rights reserved. Primary Author: Srikant Ande (Srikant.Ande<at>gmail.com)

### 📜 License
This project is licensed under the GNU General Public License v3.0 (GPL-3.0).

For the full license text, please see: [http://www.gnu.org/licenses/agpl-3.0.html](https://www.gnu.org/licenses/gpl-3.0.en.html)

## Snapshots of Drishyata

### Error screen when Sentinel is unavilable or not reachable

<img width="3584" height="1194" alt="image" src="https://github.com/user-attachments/assets/6e024f4f-af36-486c-914f-996b58c6b6cc" />

### Live Redis and Sentinel dashboards

<img width="3584" height="1826" alt="image" src="https://github.com/user-attachments/assets/1184db41-93d2-4666-b9cb-212967072398" />

<img width="3584" height="1980" alt="image" src="https://github.com/user-attachments/assets/c6af250c-d698-4967-9475-6191286974ef" />

<img width="3584" height="1770" alt="image" src="https://github.com/user-attachments/assets/b06a459e-29e9-44c5-ba0b-13329afbaf25" />

### History Redis and Sentinel dashboards

<img width="3562" height="1742" alt="image" src="https://github.com/user-attachments/assets/8c94d54f-bfac-453e-b2b8-ed765e646820" />

<img width="3584" height="1534" alt="image" src="https://github.com/user-attachments/assets/a53cd4a9-f80b-4812-acba-f2de243c22d0" />
