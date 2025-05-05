# 🏋️ Redline Fitness Games Results Visualizer

This project is a web-based application to search, filter, and visualize results from the **Redline Fitness Games** events (2023 and 2024). It provides an intuitive UI for athletes and enthusiasts to explore competitor performances across years, categories, and locations.

> 🔗 This project is independently developed and not affiliated with [redlinefitnessgames.com](https://redlinefitnessgames.com/).

---

## 🚀 Features

- 🔍 **Search** competitors by name
- 📊 **Full-width dynamic tables** using DataTables
- 📁 **Results** page with filtering by year, gender, category, and location
- 📱 Responsive layout, optimized for desktop and mobile
- 💾 Clean UI using Bootstrap and custom styling
- 🎯 Built for scalability, performance, and easy navigation

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

- Python 3.10+
- Flask
- HTML, CSS, JS
- jQuery & Bootstrap 4
- DataTables (with scroll and fixed header support)

---

## 🧠 SEO & Optimization

- ✅ `robots.txt` and `sitemap.xml` provided for search indexing
- ✅ Semantic HTML structure
- ✅ Clean URLs and descriptive titles
- ✅ Mobile-friendly and responsive layout
- ✅ Fast loading and lightweight JS

---

## 📦 Setup

```bash
git clone https://github.com/yourusername/redline-results.git
cd redline-results
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask run
