# Design Unit and Integration Tests with GitHub Actions CI

Create a comprehensive testing suite for CatWeazle using Python's standard `unittest` framework, and set up a GitHub Actions workflow to run the tests automatically on code pushes and pull requests.

## User Review Required

> [!NOTE]
> All tests will be built using the standard Python library `unittest` (as requested) and will run completely isolated without requiring a live MongoDB or LDAP instance. All database operations and external HTTP calls will be mocked using `unittest.mock.AsyncMock`.

## Proposed Changes

### [New Tests]

We will create a comprehensive suite of unit and integration tests under the `tests/` directory:

#### 1. Authorization Unit Tests
* **[tests/test_authorize.py](file:///home/schlitzer/PycharmProjects/CatWeazle/tests/test_authorize.py)**:
  * Tests the `Authorize` class methods: `get_user`, `require_admin`, `require_user`, and `require_permission`.

#### 2. Webhook Execution Unit Tests
* **[tests/test_webhook_executor.py](file:///home/schlitzer/PycharmProjects/CatWeazle/tests/test_webhook_executor.py)**:
  * Tests dynamic placeholder replacement (`{instance:id}`, `{instance:meta:role}`, `{secret:SECRET_ID}`, `{trigger}`).
  * Tests the request dispatching logic (methods, params, body, basic auth, ssl certs).

#### 3. Endpoint Integration Tests
We will build tests utilizing the FastAPI `TestClient` to hit all API routes, mocking database/auth logic to ensure high coverage:
* **[tests/test_endpoint_authenticate.py](file:///home/schlitzer/PycharmProjects/CatWeazle/tests/test_endpoint_authenticate.py)**:
  * Tests login, session retrieval, and logout endpoints.
* **[tests/test_endpoint_users.py](file:///home/schlitzer/PycharmProjects/CatWeazle/tests/test_endpoint_users.py)**:
  * Tests user creation, retrieval, updates, deletion, and searches.
* **[tests/test_endpoint_users_credentials.py](file:///home/schlitzer/PycharmProjects/CatWeazle/tests/test_endpoint_users_credentials.py)**:
  * Tests API key/credentials creation, retrieval, deletion, and search.
* **[tests/test_endpoint_instances.py](file:///home/schlitzer/PycharmProjects/CatWeazle/tests/test_endpoint_instances.py)**:
  * Tests instance registration, details retrieval, search filters, updates, and deletion.
* **[tests/test_endpoint_permissions.py](file:///home/schlitzer/PycharmProjects/CatWeazle/tests/test_endpoint_permissions.py)**:
  * Tests permission definitions, lists, updates, and deletion.
* **[tests/test_endpoint_secrets.py](file:///home/schlitzer/PycharmProjects/CatWeazle/tests/test_endpoint_secrets.py)**:
  * Tests secret storage, lists, retrieval, updates, and deletion.
* **[tests/test_endpoint_webhooks.py](file:///home/schlitzer/PycharmProjects/CatWeazle/tests/test_endpoint_webhooks.py)**:
  * Tests webhook registration, lists, updates, and deletion.
* **[tests/test_endpoint_webhook_logs.py](file:///home/schlitzer/PycharmProjects/CatWeazle/tests/test_endpoint_webhook_logs.py)**:
  * Tests searching and paginating webhook execution logs.

---

### [GitHub Actions CI Setup]

#### [NEW] [test.yml](file:///home/schlitzer/PycharmProjects/CatWeazle/.github/workflows/test.yml)
- GitHub Actions workflow running on pushes and pull requests to `main` or other target branches.
- Installs requirements and runs the `unittest` discover suite.

---

## Verification Plan

### Automated Tests
- Run `python -m unittest discover -s tests` to verify all test cases pass locally.
