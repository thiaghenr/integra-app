
# Skill: Frontend

Follow these conventions when creating or modifying Jinja2 templates and static files.

## Design tokens

```css
--brand-blue: #2D7DD2;
--bg-white: #FFFFFF;
--bg-sidebar: #F4F6F8;
--text-dark: #1A1A2E;
--text-muted: #6B7280;
--success: #16A34A;
--danger: #DC2626;
--warning: #D97706;
```

## Layout

- Fixed left sidebar: 240px wide, background `#F4F6F8`
- Main content area: takes remaining width, white background
- Top header: shows clinic name + logged-in user name
- Sidebar collapses on mobile (hamburger toggle)
- Max content width on forms: 640px, centered

## Template structure

Every page extends `base.html`:

```html
{% extends "base.html" %}

{% block title %}Patients — Integra{% endblock %}

{% block content %}
  <div class="page-header">
    <h1>Patients</h1>
    <a href="/patients/new" class="btn btn-primary">New Patient</a>
  </div>

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for category, message in messages %}
        <div class="alert alert-{{ category }}">{{ message }}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}

  {# page content here #}
{% endblock %}
```

## Tables

```html
<table class="table">
  <thead>
    <tr>
      <th>Name</th>
      <th>Phone</th>
      <th>Status</th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    {% for patient in patients %}
    <tr>
      <td>{{ patient.full_name }}</td>
      <td>{{ patient.phone or "—" }}</td>
      <td><span class="badge badge-{{ patient.is_active | status_class }}">{{ patient.is_active | status_label }}</span></td>
      <td class="actions">
        <a href="/patients/{{ patient.id }}/edit">Edit</a>
        <form method="POST" action="/patients/{{ patient.id }}/delete" style="display:inline">
          <button type="submit" onclick="return confirm('Are you sure?')">Delete</button>
        </form>
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>
```

## Forms

```html
<form method="POST" action="/patients/new">
  <div class="form-group">
    <label for="full_name">Full name</label>
    <input type="text" id="full_name" name="full_name" value="{{ form.full_name or '' }}" required>
    {% if errors.full_name %}
      <span class="form-error">{{ errors.full_name }}</span>
    {% endif %}
  </div>
  <div class="form-actions">
    <button type="submit" class="btn btn-primary">Save</button>
    <a href="/patients" class="btn btn-secondary">Cancel</a>
  </div>
</form>
```

## Status badges (pill-shaped, color-coded)

| Status    | Color  |
| --------- | ------ |
| scheduled | blue   |
| confirmed | green  |
| completed | purple |
| cancelled | gray   |
| no_show   | red    |

## Flash messages

```python
# In router (after redirect)
request.session["flash"] = {"category": "success", "message": "Patient saved."}
```

Auto-dismiss after 4 seconds via `static/js/main.js`.

## Rules

- Never use React, Vue, or any JS framework — vanilla JS only
- JS only for lightweight interactions: modal toggles, date pickers, dynamic selects
- Never inline styles — always use CSS classes in `static/css/style.css`
- Always show empty state when a list has no items:
  ```html
  {% if not patients %}
    <p class="empty-state">No patients found.</p>
  {% endif %}
  ```
- Forms always use POST (never PUT/DELETE from HTML — use POST with a hidden `_method` field if needed)
