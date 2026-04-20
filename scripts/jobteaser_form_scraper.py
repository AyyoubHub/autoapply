import json
import os
import logging

def extract_form_fields(driver, job_title="Unknown", company_name="Unknown", href="Unknown"):
    """
    Extracts form fields from the current JobTeaser application modal.
    Saves results to scratch/jobteaser_form_fields.json and updates docs/jobteaser_form_composition.md.
    """
    try:
        # Enhanced extraction script to capture values, options, and custom components
        extraction_script = """
        let elements = [];
        let form = document.querySelector('.ApplicationFlow_content__HXZmt') || document.querySelector('#application-flow-form') || document.body;
        
        // Scroll to bottom and back to top to trigger any lazy-loaded sections (like cover letter)
        form.scrollBy(0, 1000);
        
        form.querySelectorAll('input, select, textarea, [role="combobox"]').forEach(el => {
            let label = '';
            
            // 1. Direct label lookup
            if (el.id) {
                let l = document.querySelector('label[for="' + el.id + '"]');
                if (l) label = l.innerText;
            }
            
            // 2. Aria-labelledby lookup
            if (!label && el.getAttribute('aria-labelledby')) {
                let l = document.getElementById(el.getAttribute('aria-labelledby'));
                if (l) label = l.innerText;
            }
            
            // 3. Parent container lookup (for sk-Select and JobTeaser custom patterns)
            if (!label) {
                let wrapper = el.closest('[data-testid^="input-wrapper-"]') || 
                              el.closest('.CardWrapper_main__jCbr4') || 
                              el.closest('.CoverLetterContent_main__Z4CRS') ||
                              el.parentElement;
                if (wrapper) {
                    let labelEl = wrapper.querySelector('label') || wrapper.querySelector('p, span, h3, h4');
                    if (labelEl) label = labelEl.innerText;
                }
            }
            
            if (!label) label = el.placeholder || el.name || 'unlabeled';
            
            let options = [];
            if (el.tagName === 'SELECT') {
                Array.from(el.options).forEach(opt => {
                    options.push({ value: opt.value, text: opt.text });
                });
            } else if (el.type === 'checkbox' || el.type === 'radio') {
                options.push({ value: el.value, checked: el.checked });
            } else if (el.getAttribute('role') === 'combobox') {
                options.push({ type: 'custom-dropdown', info: 'Requires interaction to see options' });
            }
            
            elements.push({
                tag: el.tagName,
                type: el.type || el.getAttribute('role'),
                name: el.name || el.id,
                id: el.id,
                label: label.trim().split('\\n')[0].trim(), // Take only first line of multi-line labels
                value: el.value || (el.tagName === 'TEXTAREA' ? el.innerText : ''),
                required: el.required || el.getAttribute('aria-required') === 'true',
                options: options.length > 0 ? options : null
            });
        });
        return elements;
        """
        new_fields = driver.execute_script(extraction_script)
        
        out_path = os.path.join(os.path.dirname(__file__), "../scratch/jobteaser_form_fields.json")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        
        # Load existing fields to merge
        existing_fields = []
        if os.path.exists(out_path):
            try:
                with open(out_path, "r", encoding="utf-8") as f:
                    existing_fields = json.load(f)
            except Exception:
                existing_fields = []
        
        # Helper to create a unique fingerprint for a field
        def get_fingerprint(f):
            return f"{f.get('tag')}|{f.get('name')}|{f.get('id')}|{f.get('label')}"
        
        existing_fingerprints = {get_fingerprint(f) for f in existing_fields}
        
        appended_count = 0
        for f in new_fields:
            fingerprint = get_fingerprint(f)
            if fingerprint not in existing_fingerprints:
                existing_fields.append(f)
                existing_fingerprints.add(fingerprint)
                appended_count += 1
            else:
                # Update value and options even if it exists
                for ex in existing_fields:
                    if get_fingerprint(ex) == fingerprint:
                        ex["value"] = f["value"]
                        ex["options"] = f.get("options")
                        break
        
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(existing_fields, f, indent=2, ensure_ascii=False)
        
        # Generate/Update Markdown Report
        md_path = os.path.join(os.path.dirname(__file__), "../docs/jobteaser_form_composition.md")
        try:
            with open(md_path, "w", encoding="utf-8") as f:
                f.write("# JobTeaser Form Composition Analysis\n\n")
                f.write(f"**Last Job Analyzed:** {job_title} at {company_name}\n")
                f.write(f"**URL:** {href}\n\n")
                f.write("This file is automatically updated with unique form fields discovered during JobTeaser applications.\n\n")
                f.write("| Label | Tag | Type | Name | Required | Captured Value | Options / State |\n")
                f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
                for field in existing_fields:
                    label = field.get("label", "N/A")
                    tag = field.get("tag", "N/A")
                    ftype = field.get("type", "N/A")
                    fname = field.get("name", "N/A")
                    freq = "Yes" if field.get("required") else "No"
                    fval = (field.get("value") or "").replace('|', '\\|')
                    
                    opts_str = ""
                    opts = field.get("options")
                    if opts:
                        if tag == "SELECT":
                            opts_str = ", ".join([f"{o.get('text')} ({o.get('value')})" for o in opts])
                        elif tag == "DIV" and ftype == "combobox":
                            opts_str = "Custom Dropdown (needs interaction)"
                        elif ftype in ["checkbox", "radio"]:
                            opts_str = f"Checked: {opts[0].get('checked')}"
                    
                    f.write(f"| {label} | {tag} | {ftype} | {fname} | {freq} | `{fval}` | {opts_str} |\n")
            
            logging.info("Updated Markdown report at %s", md_path)
        except Exception as e:
            logging.error("Failed to update Markdown report: %s", e)

        logging.info("Extracted %d new form fields. Total unique fields: %d", appended_count, len(existing_fields))
        return len(new_fields), appended_count, len(existing_fields)
        
    except Exception as e:
        logging.error("Failed to extract form fields: %s", e)
        return 0, 0, 0
