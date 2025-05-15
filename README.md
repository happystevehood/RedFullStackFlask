# 🏋️ Redline Fitness Games Results Explorer

This project is a web-based application to search, filter, and visualize results from the **Redline Fitness Games** events (2023 and 2024). It provides an intuitive UI for athletes and enthusiasts to explore competitor performances across years, categories, and locations.

At the time of writing this app is deployed on gcloud at the follwwoing link.
> 🔗 https://app-py-951032250531.asia-southeast1.run.app/

Other useful links are here.
> 🔗 This project is independently developed and not affiliated with [redlinefitnessgames.com](https://redlinefitnessgames.com/).
> 🔗 This development was based on my original repository [redline-fitness-results-visualisation](https://github.com/happystevehood/redline-fitness-results-visualisation)

---
![visualisation_samples](https://github.com/user-attachments/assets/3824e2f7-9f6e-488c-80ff-6412f0889c50)

## 🚀 Features

- 🔍 **Search** competitors by name
- 📊 **Full-width dynamic tables** using DataTables
- 📁 **Results** page with filtering by year, gender, category, and location
- 📱 Responsive layout, optimized for desktop and mobile
- 💾 Clean UI using Bootstrap and custom styling
- 🎯 Built for scalability, performance, and easy navigation
 
![results_sample](https://github.com/user-attachments/assets/70778bbb-4375-482d-9bf8-8b6d6ff00064)
![results_table](https://github.com/user-attachments/assets/d3c7c005-df77-4267-87ef-14c77c9de930)
![searchlist](https://github.com/user-attachments/assets/4a44683c-569f-40e3-9c73-83fe0a37fe6c)

---

## 📂 Data Sources

This project is based on publicly available Redline Fitness Games results:

- **2023 Results**
  - [Day 1](https://runnersunite.racetecresults.com/results.aspx?CId=16634&RId=1216)
  - [Day 2](https://runnersunite.racetecresults.com/results.aspx?CId=16634&RId=1217)
- **2024 Results**
  - [Day 1](https://runnersunite.racetecresults.com/results.aspx?CId=16634&RId=1251)
  - [Day 2](https://runnersunite.racetecresults.com/results.aspx?CId=16634&RId=1252)

Raw results were manually copied to Excel and exported as CSV for backend ingestion.

---

## ⚙️ Tech Stack

- Python 3.11+
- mathplotlib, pandas, seaborn
- Flask, Jinja
- HTML, CSS, JS
- jQuery & Bootstrap
- DataTables (with scroll and fixed header support)
- Google Google Cloud Run 
- Cybersecurity
- Dockers, multi-threading, multi-containers
- And much more.

---

## 🧠 SEO & Optimization

- ✅ `robots.txt` and `sitemap.xml` provided for search indexing
- ✅ Semantic HTML structure
- ✅ Clean URLs and descriptive titles
- ✅ Mobile-friendly and responsive layout
- ✅ Fast loading and lightweight JS

---

## 📦 Setup - TBC if this works as below

```bash
git https://github.com/happystevehood/RedFullStackFlask.git
cd RedFullStackFlask
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./run-scripts/run-local-dev.sh
