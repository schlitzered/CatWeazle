# UI Permissions Integration Specification

This document details the interface spec for the UI LLM to dynamically toggle the visibility of interface elements based on user permissions.

## 1. User Permissions Retrieval (`_self` endpoint)
To fetch the current logged-in user's details and active permissions, the UI should issue a GET request to:
* **Endpoint**: `GET /api/v2/users/_self`
* **Response Payload Schema** (`ModelV2UserGet`):
  ```json
  {
    "id": "john_doe",
    "name": "John Doe",
    "email": "john@example.com",
    "admin": false,
    "backend": "internal",
    "permissions": [
      "INSTANCE:POST",
      "WEBHOOK:POST",
      "WEBHOOK_LOG:GET"
    ]
  }
  ```

---

## 2. Dynamic UI Elements Visibility Mapping

The UI should hide/disable or show/enable specific components and buttons based on the items present in the user's `permissions` array:

| UI Endpoint / View | Action / Element | Required Permission |
| :--- | :--- | :--- |
| **Instances View** | Create Instance Button / Dialog | `INSTANCE:POST` |
| **Instances View** | Update Instance Action | `INSTANCE:POST` |
| **Instances View** | Delete Instance Button | `INSTANCE:DELETE` |
| **Webhooks View** | Create Webhook Form | `WEBHOOK:POST` |
| **Webhooks View** | Edit Webhook Button | `WEBHOOK:POST` |
| **Webhooks View** | Delete Webhook Button | `WEBHOOK:DELETE` |
| **Secrets View** | Create Secret Form | `SECRET:POST` |
| **Secrets View** | Edit Secret Button | `SECRET:POST` |
| **Secrets View** | Delete Secret Button | `SECRET:DELETE` |
| **Webhook Logs View**| View Webhook Logs Dashboard | `WEBHOOK_LOG:GET` |

### Note on Admins
* If `"admin": true` is returned by the `_self` endpoint, the `permissions` array will automatically populate with all available permissions:
  `["INSTANCE:POST", "INSTANCE:DELETE", "WEBHOOK:POST", "WEBHOOK:DELETE", "SECRET:POST", "SECRET:DELETE", "WEBHOOK_LOG:GET"]`
* The UI LLM should write a simple permission checking helper in the frontend:
  ```javascript
  function hasPermission(user, permission) {
    return user.admin || (user.permissions && user.permissions.includes(permission));
  }
  ```

---

## 3. Managing Permissions (Permissions UI)
Only administrators (`admin: true`) can access the Permissions management UI.
* **Retrieve Permissions**: `GET /api/v2/permissions`
* **Create/Grant Permissions**: `POST /api/v2/permissions/{permission_id}`
  * Payload:
    ```json
    {
      "users": ["john_doe"],
      "permissions": ["INSTANCE:POST", "WEBHOOK:POST"]
    }
    ```
* **Edit/Revoke Permissions**: `PUT /api/v2/permissions/{permission_id}`
* **Delete Permissions**: `DELETE /api/v2/permissions/{permission_id}`
