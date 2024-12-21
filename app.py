import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd


def checkExist(db, user):
    return db.execute("SELECT * FROM users WHERE username = ?", user)


def getSumry(db, user_id):
    """
    Get summary of user's transactions.

    Args:
        user_id (int): The ID of the user.

    Returns:
        list: A list containing dictionaries with the summary data for each symbol.
    """
    # Execute SQL query to get summary data
    summary = db.execute("""
        SELECT
            simbolo,
            SUM(cantidadRestante) AS acciones_total,
            SUM(precio * cantidadRestante) AS inversion_total
        FROM
            Transacciones
        WHERE
            userID = ?
            AND cantidadTransada > 0
            AND cantidadRestante > 0
        GROUP BY
            simbolo
        HAVING
            SUM(cantidadRestante) > 0
    """, user_id)

    return summary


def getUsersStoks(db, user, order, conditions):
    return db.execute(
        f"SELECT fecha, simbolo, precio, transaccionID, cantidadTransada, cantidadRestante,balance,total_transado FROM Transacciones WHERE userID = ? {conditions} ORDER BY {order}",
        user,
    )


def renderHistory(template, order, conditions):
    shares = getUsersStoks(db, session["user_id"], order, conditions)
    cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
    sumary = getSumry(db, session["user_id"])

    invested = 0
    for sum in sumary:
        invested = invested + sum["inversion_total"]

    """Sell shares of stock"""
    return render_template(
        template, shares=shares, invested=invested, cash=cash[0]["cash"], sumary=sumary
    )


# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    return renderHistory("index.html", "fecha ASC", "AND cantidadTransada > 0 AND cantidadRestante != 0")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        ticket = request.form.get("symbol")
        if ticket == "":
            return apology("must provide ticket", 400)

        if ticket is None:
            return apology("Ticket not found", 400)

        shareInfo = lookup(ticket)
        if shareInfo is None:
            return apology("Ticket not found", 400)
        else:
            shares = request.form.get("shares")
            if shares == "":
                return apology("must provide quantity", 400)
            if not shares:
                return apology("must provide quantity", 403)
            try:
                shares = int(shares)
                if shares <= 0:
                    return apology("shares must be positive integers", 400)
            except ValueError:
                return apology("shares must be numbers only", 400)
            totalSpent = shares * shareInfo["price"]
            print(totalSpent)
            # Ensure password was submitted
            rows = db.execute("SELECT * FROM users WHERE id  = ?", session["user_id"])
            balance = rows[0]["cash"]
            balance = balance - totalSpent
            if balance < 0:
                return apology("Not enougth cash")
            db.execute(
                "UPDATE users SET cash = ? WHERE id = ?", balance, session["user_id"]
            )

            db.execute(
                "INSERT INTO Transacciones (userID, simbolo, cantidadTransada, cantidadRestante, balance, precio,total_transado) VALUES (?, ?, ?, ?, ?, ?,?)",
                rows[0]["id"],
                shareInfo["symbol"],
                shares,
                shares,
                balance,
                shareInfo["price"],
                shareInfo["price"]*shares
            )
            flash(f"Bought {shares} of {shareInfo['symbol']} for {shareInfo['price']}, Updated cash: {usd(balance)}")
            return redirect("/")
    else:
        return render_template("buy.html", transactionStatus=False)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return renderHistory("history.html", "fecha ASC", "AND cantidadTransada != 0 ")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = checkExist(db, request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        ticker = request.form.get("symbol")  # Get ticker and strip whitespace
        if ticker == "":  # Check if the ticker is empty after stripping whitespace
            return apology("Ticker symbol required", 400)

        shareInfo = lookup(ticker)  # Lookup the ticker
        if not shareInfo:
            return apology("Ticker symbol not found", 400)  # Use 404 for "Not Found"
        else:
            # Ensure correct spelling of template file
            return render_template("quoteAnwer.html", requesting=True, shareInfo=shareInfo)

    # User reached route via GET (as by clicking a link or via redirect)
    elif request.method == "GET":
        return render_template("quote.html", requesting=False, shareInfo=None)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            return apology("must provide username", 400)

        if len(checkExist(db, username)) > 0:
            return apology("This username is not available", 400)

        if not password:
            return apology("must provide password", 400)

        if not confirmation:
            return apology("must provide confirmation", 400)

        if password != confirmation:
            return apology("password and confirmation must match", 400)

        db.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?)",
            username,
            generate_password_hash(password)
        )
        user = checkExist(db, username)
        session["user_id"] = user[0]["id"]
        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        simbolo = request.form.get("symbol")
        transaction = request.form.get("shares")
        transaction = int(transaction)

        # Obtiene la cantidad total de acciones disponibles para vender
        totalShares = db.execute(
            "SELECT SUM(cantidadRestante) AS total_cantidad_restante FROM Transacciones WHERE userID = ? AND simbolo = ? AND cantidadRestante > 0 AND cantidadTransada > 0;",
            session["user_id"],
            simbolo
        )
        totalShares = totalShares[0]["total_cantidad_restante"]

        if totalShares is None:
            return apology("not found")

        if totalShares < transaction:
            return apology("You don't have enough shares to sell that many.")

        # Obtiene las transacciones donde hay acciones disponibles
        sharesCuantity = db.execute(
            "SELECT * FROM Transacciones WHERE userID = ? AND simbolo = ? AND cantidadRestante > 0 AND cantidadTransada > 0",
            session["user_id"],
            simbolo
        )

        # Información del ticket
        ticketInfo = lookup(simbolo)

        # Variables para la cantidad de acciones que quedan por vender
        sharesLeft = transaction

        # Obtiene el saldo actual del usuario
        user = db.execute(
            "SELECT cash FROM users WHERE id = ?",
            session["user_id"]
        )
        user_cash = user[0]["cash"]

        for query in sharesCuantity:
            if sharesLeft == 0:
                break

            if query["cantidadRestante"] <= sharesLeft:
                sharesToSell = query["cantidadRestante"]
            else:
                sharesToSell = sharesLeft

            # Actualiza las acciones restantes
            sharesLeft -= sharesToSell

            # Actualiza las transacciones en la base de datos
            db.execute(
                "UPDATE Transacciones SET cantidadRestante = cantidadRestante - ? WHERE userID = ? AND transaccionID = ?",
                sharesToSell,
                session["user_id"],
                query["transaccionID"],
            )

            # Inserta una nueva transacción con la venta
            db.execute(
                "INSERT INTO Transacciones (userID, simbolo, cantidadTransada, cantidadRestante, balance, precio, total_transado) VALUES (?, ?, ?, ?, ?, ?, ?)",
                session["user_id"],
                simbolo,
                -sharesToSell,
                0,  # Cantidad restante después de vender es 0
                user_cash + (ticketInfo["price"] * sharesToSell),
                ticketInfo["price"],
                (sharesToSell * ticketInfo["price"]) * -1
            )

            # Actualiza el saldo del usuario
            user_cash += ticketInfo["price"] * sharesToSell

        # Actualiza el saldo del usuario en la base de datos
        db.execute(
            "UPDATE users SET cash = ? WHERE id = ?",
            user_cash,
            session["user_id"]
        )

        flash(f"Sold {transaction} of {simbolo} for {usd(ticketInfo['price'])} each with a total of {usd(ticketInfo['price']*transaction)}")
        return redirect("/")

    return renderHistory(
        "sell.html",
        "simbolo DESC, precio DESC",
        "AND cantidadTransada > 0 AND cantidadRestante != 0",
    )
