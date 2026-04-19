# JobTeaser Filter Parameters Guide

This document provides a comprehensive list of the URL query parameters used to apply filters on the JobTeaser job search page (`https://www.jobteaser.com/fr/job-offers`). You can use these parameters to programmatically filter search results in the automation script. Many of these accept multiple values by repeating the parameter (e.g. `&languages=fr&languages=en`).

## Core Parameters

### 1. Application Type (Type de candidature)
- **Candidature Simplifiée (Easy Apply Only):** `candidacy_type=INTERNAL`
  *(Note: This is the most critical parameter to ensure the bot only processes jobs that can be applied to natively within JobTeaser.)*

### 2. Contract Type (`contract`)
This parameter can be passed multiple times (e.g., `&contract=cdi&contract=cdd`) to select multiple types.
- **Stage (Internship):** `contract=internship`
- **Alternance (Apprenticeship):** `contract=alternating`
- **CDD (Fixed-term):** `contract=cdd`
- **CDI (Permanent):** `contract=cdi`
- **Graduate Program:** `contract=graduate_program`
- **VIE / VIA:** `contract=vie_via`
- **Job Étudiant:** `contract=student_job`
- **Recherche / Thèse:** `contract=research_thesis`
- **Freelance / Indépendant:** `contract=freelance`

## Extended Criteria (Plus de critères)

### 3. Experience Level (`work_experience`)
*(Note: parameter may be named `work_experience_code` or `work_experience` depending on the exact URL structure, though usually JobTeaser uses `work_experience_code`)*
- **Étudiant / jeune diplômé:** `young_graduate`
- **3 à 5 ans:** `three_to_five_years`
- **6 à 10 ans:** `six_to_ten_years`
- **Plus de 10 ans:** `more_than_ten_years`

### 4. Duration (`duration` / `contract_duration`)
- **1 - 3 mois:** `3`
- **4 - 6 mois:** `6`
- **7 - 9 mois:** `9`
- **10 - 12 mois:** `12`
- **13 - 18 mois:** `18`
- **19 - 24 mois:** `24`
- **25 - 36 mois:** `36`

### 5. Language (`languages`)
- **Français:** `fr`
- **Anglais:** `en`
- **Espagnol:** `es`
- **Allemand:** `de`
- **Danois:** `da`
- **Suédois:** `sv`

### 6. Study Levels (Niveaux d'étude) (`study_levels`)
- **Pas de niveau prérequis:** `1`
- **Bac+2:** `2`
- **Bac+3, Bachelor:** `3`
- **Niveau Master, MSc ou Programme Grande Ecole:** `4`
- **Doctorat:** `5`
- **Bac, Bac Pro, CAP, BEP:** `6`

### 7. Remote Work (Télétravail) (`remote_types`)
- **Télétravail ponctuel autorisé:** `remote_partial`
- **Poste ouvert au télétravail à temps plein:** `remote_full`

### 8. Company Category (Catégorie d'entreprise) (`company_business_type`)
- **Grande entreprise:** `large`
- **Start-up:** `startup`
- **PME:** `sme`
- **Association / Institution publique / Laboratoire:** `ngo_public_lab`
- **Collectif:** `collective`

### 9. Start Date (Date de début) (`start_date`)
- **Dès que possible:** `0`
- **Specific month:** Format `YYYY_MM` (e.g. `2026_04` for Avril 2026)

### 10. Job Function (Fonction) (`job_function_ids[]`)
These IDs are used to filter by specific job roles. You can select multiple functions by repeating the parameter.

| Category | Job Function | Internal ID |
| :--- | :--- | :--- |
| **Admin, RH & Juridique** | Administratif | 16 |
| | Droit des affaires | 20 |
| | Ressources Humaines | 11 |
| **Business & Management** | Achats | 1 |
| | Business dev / Vente | 2 |
| | Conseil | 3 |
| | Entrepreneuriat | 4 |
| | Import / Export | 5 |
| | Logistique & Transport | 6 |
| | Management / Stratégie | 7 |
| | Marketing | 8 |
| | Product Management | 9 |
| | Relation client / SAV | 10 |
| **Finance & Audit** | Audit | 12 |
| | Comptabilité | 13 |
| | Finance d'entreprise | 14 |
| | Finance de marché | 15 |
| **Communication & Médias**| Communication | 17 |
| | Evenementiel | 18 |
| | Journalisme / Traduction | 19 |
| **Ingénierie** | BTP / Génie civil | 21 |
| | Electronique / Signal | 22 |
| | Energie & Environnement | 23 |
| | Industrie | 24 |
| | Mécanique | 26 |
| | Qualité & Maintenance | 27 |
| | R&D | 28 |
| **Technologie** | Data | 29 |
| | Développement Informatique| 30 |
| | Infra, Réseaux & Télécoms | 31 |
| | Webdesign & Ergonomie | 33 |
| | Gestion de projet IT | 34 |

### 11. Company Sector (Secteur d'activité) (`domain_ids[]`)
These IDs are used to filter by the industry sector of the company.

| Category | Sector | Internal ID |
| :--- | :--- | :--- |
| **Audit / Conseil / Juridique**| Conseil | 20 |
| | Conseil en stratégie | 25 |
| **Banque / Finance** | Banque / Finance | 5 |
| | Assurance | 6 |
| **BTP / Immobilier** | Immobilier | 7 |
| | BTP / Urbanisme | 8 |
| | Architecture / Design | 9 |
| **Commerce / Distribution** | Luxe / Mode | 10 |
| **Communication / Médias** | Communication / Médias | 11 |
| | Presse / Editions | 12 |
| **Autres** | Énergie / Environnement | 13 |
| | Enseignement / Recherche | 14 |

## Example Usage
To construct a search URL that filters for **CDI** and **CDD** jobs, for **3 to 5 years experience**, requiring **English**, strictly allowing **Easy Apply**, and in the **Développement Informatique** function:
```
https://www.jobteaser.com/fr/job-offers?candidacy_type=INTERNAL&contract=cdi&contract=cdd&work_experience_code=three_to_five_years&languages[]=en&job_function_ids[]=30&page=1
```
