"""Hardcoded Northwind prompt builder (Phase 1).

Phase 3 will replace this with RAG-retrieved schema chunks. Phase 1 keeps it
simple: paste the full schema, three few-shots, and one system instruction.
"""

SYSTEM_INSTRUCTION = """You are an expert SQLite SQL assistant. Given a schema and a question in natural \
language, produce a single safe SELECT query and a short explanation.

RULES — non-negotiable:
1. Output ONLY a single SELECT statement. NEVER INSERT, UPDATE, DELETE, DROP, ALTER, \
CREATE, PRAGMA, ATTACH, or any other DDL/DML.
2. Use SQLite dialect only — no Postgres- or MySQL-only functions (e.g. no DATE_TRUNC, \
no EXTRACT, no NOW(); use strftime, julianday, date()).
3. Identifiers with spaces MUST be double-quoted. The table named Order Details MUST \
always be written as "Order Details".
4. Always include LIMIT 100 (or a smaller user-requested limit) unless the user \
explicitly asks for "all" rows.
5. Use only the exact column names from the schema below — do not invent columns.
6. The Discontinued column on Products is TEXT (values "0" or "1"), not a boolean.
7. Choose chart_hint as follows:
   - "scalar" — a single number (e.g. COUNT, AVG of one value)
   - "line"   — time series (any ORDER BY of a date/time column with one numeric metric)
   - "bar"    — categorical comparison (group-by category with one numeric metric)
   - "pie"    — parts of a whole with at most 6 categories
   - "table"  — anything else, especially multi-column results
8. The explanation is one or two short plain-English sentences."""

SCHEMA_TEXT = """SCHEMA — Northwind (SQLite). Row counts shown in parentheses.

- Categories (8) — CategoryID INTEGER PK, CategoryName TEXT, Description TEXT, Picture BLOB

- Customers (93) — CustomerID TEXT PK, CompanyName TEXT, ContactName TEXT, ContactTitle TEXT, \
Address TEXT, City TEXT, Region TEXT, PostalCode TEXT, Country TEXT, Phone TEXT, Fax TEXT

- Employees (9) — EmployeeID INTEGER PK, LastName TEXT, FirstName TEXT, Title TEXT, \
TitleOfCourtesy TEXT, BirthDate DATE, HireDate DATE, Address TEXT, City TEXT, Region TEXT, \
PostalCode TEXT, Country TEXT, HomePhone TEXT, Extension TEXT, Notes TEXT, \
ReportsTo INTEGER, PhotoPath TEXT
  FKs: ReportsTo -> Employees.EmployeeID  (self-reference; manager hierarchy)

- Orders (16282) — OrderID INTEGER PK, CustomerID TEXT, EmployeeID INTEGER, \
OrderDate DATETIME, RequiredDate DATETIME, ShippedDate DATETIME, ShipVia INTEGER, \
Freight NUMERIC, ShipName TEXT, ShipAddress TEXT, ShipCity TEXT, ShipRegion TEXT, \
ShipPostalCode TEXT, ShipCountry TEXT
  FKs: CustomerID -> Customers.CustomerID, EmployeeID -> Employees.EmployeeID, \
ShipVia -> Shippers.ShipperID

- "Order Details" (609283) — OrderID INTEGER PK, ProductID INTEGER PK, \
UnitPrice NUMERIC, Quantity INTEGER, Discount REAL
  FKs: OrderID -> Orders.OrderID, ProductID -> Products.ProductID
  NOTE: line-revenue = UnitPrice * Quantity * (1 - Discount)

- Products (77) — ProductID INTEGER PK, ProductName TEXT, SupplierID INTEGER, \
CategoryID INTEGER, QuantityPerUnit TEXT, UnitPrice NUMERIC, UnitsInStock INTEGER, \
UnitsOnOrder INTEGER, ReorderLevel INTEGER, Discontinued TEXT
  FKs: SupplierID -> Suppliers.SupplierID, CategoryID -> Categories.CategoryID

- Suppliers (29) — SupplierID INTEGER PK, CompanyName TEXT, ContactName TEXT, \
ContactTitle TEXT, Address TEXT, City TEXT, Region TEXT, PostalCode TEXT, \
Country TEXT, Phone TEXT, Fax TEXT, HomePage TEXT

- Shippers (3) — ShipperID INTEGER PK, CompanyName TEXT, Phone TEXT

- Regions (4) — RegionID INTEGER PK, RegionDescription TEXT

- Territories (53) — TerritoryID TEXT PK, TerritoryDescription TEXT, RegionID INTEGER
  FKs: RegionID -> Regions.RegionID

- EmployeeTerritories (49) — EmployeeID INTEGER PK, TerritoryID TEXT PK
  FKs: EmployeeID -> Employees.EmployeeID, TerritoryID -> Territories.TerritoryID

- CustomerDemographics (0, EMPTY) — CustomerTypeID TEXT PK, CustomerDesc TEXT
- CustomerCustomerDemo  (0, EMPTY) — CustomerID TEXT PK, CustomerTypeID TEXT PK
  NOTE: the two demographics tables are empty — avoid them unless explicitly asked."""

FEW_SHOTS = """EXAMPLES:

Q: How many customers are based in Germany?
A: {
  "sql": "SELECT COUNT(*) AS GermanCustomers FROM Customers WHERE Country = 'Germany'",
  "explanation": "Counts the customers whose Country column equals 'Germany'.",
  "chart_hint": "scalar"
}

Q: List the top 5 customers by number of orders placed.
A: {
  "sql": "SELECT c.CustomerID, c.CompanyName, COUNT(o.OrderID) AS OrderCount FROM Customers c JOIN Orders o ON c.CustomerID = o.CustomerID GROUP BY c.CustomerID, c.CompanyName ORDER BY OrderCount DESC LIMIT 5",
  "explanation": "Joins Customers with Orders, counts orders per customer, and returns the top 5.",
  "chart_hint": "bar"
}

Q: What were the top 5 product categories by total revenue?
A: {
  "sql": "SELECT cat.CategoryName, SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) AS Revenue FROM \\"Order Details\\" od JOIN Products p ON od.ProductID = p.ProductID JOIN Categories cat ON p.CategoryID = cat.CategoryID GROUP BY cat.CategoryID, cat.CategoryName ORDER BY Revenue DESC LIMIT 5",
  "explanation": "Aggregates line-item revenue (UnitPrice * Quantity * (1 - Discount)) from \\"Order Details\\", groups by category, and returns the top 5.",
  "chart_hint": "bar"
}"""


def build_prompt(question: str, database_id: str) -> tuple[str, str]:
    """Return (system_instruction, user_prompt) for the given question.

    Phase 1 only supports database_id == "northwind".
    """
    if database_id != "northwind":
        raise ValueError(
            f"Phase 1 only supports database_id='northwind', got '{database_id}'"
        )

    user_prompt = (
        f"{SCHEMA_TEXT}\n\n"
        f"{FEW_SHOTS}\n\n"
        f"Q: {question.strip()}\n"
        f"A:"
    )
    return SYSTEM_INSTRUCTION, user_prompt
