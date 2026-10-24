.pragma library
// CEDAR Calculator engine. Pure arithmetic over finite decimals; no eval, no
// Function, no I/O, no access to anything but the expression string.
//
// Contract
//   evaluate(expression) -> { ok: true,  value: Number, text: String }
//                        -> { ok: false, error: String }
//   It never throws to the caller.
//
// Grammar (ASCII only, spaces allowed between tokens)
//   sum      := product (("+" | "-") product)*
//   product  := unary (("*" | "/") unary)*
//   unary    := ("-" | "+") unary | power
//   power    := postfix ("^" unary)?           right associative: 2^3^2 = 2^(3^2)
//   postfix  := primary "%"*                   x% = x / 100 (not modulo)
//   primary  := number | "(" sum ")"
//   number   := mantissa [("e" | "E") ["+" | "-"] digits]
//   mantissa := digits ["." digits*] | "." digits
//              plain or scientific decimals (1.5, .5, 3., 1e5, 2.5E-3); no 0x10, 1_000
//
// A result's text always re-parses to the same value (evaluate(r.text)), so the
// UI may chain results such as "(1.0715086071863e+301)*2".
//
// Precedence notes: -2^2 = -4 (sign applies after the power); 50% binds to its
// own operand, so 200*10% = 20 and 9^50% = 3.
//
// Numbers are standard IEEE doubles, not arbitrary precision. The final result
// is rounded to 14 significant digits so 0.1+0.2 reads 0.3; intermediate steps
// are not rounded. Consequences the UI should treat as approximation, not bugs:
//   - integers beyond 14 digits are rounded (2^60 -> 1.1529215046068e+18) and
//     shown in exponent form so no padded zeros look exact;
//   - tiny cancellation residue is not hidden (0.1+0.2-0.3 -> 5.5511151231258e-17),
//     because an absolute epsilon would also erase real tiny results;
//   - results below about 5e-324 underflow quietly to 0 (0.1^400 -> 0);
//   - results beyond about 1.8e308 are refused as "Result is too large".

var MAX_LENGTH = 256;        // characters, after trimming
var MAX_TOKENS = 128;
var MAX_DEPTH = 32;          // nested parentheses plus chained unary signs
var MAX_EXPONENT = 1000;     // |power| in a ^ b; larger is refused up front
var SIGNIFICANT_DIGITS = 14;

function evaluate(expression) {
    var text;
    try {
        text = expression == null ? "" : String(expression);
    } catch (e) {
        return fail("Enter an expression");
    }
    try {
        return success(run(text));
    } catch (err) {
        if (err && err.calculator) return fail(err.message);
        // Unexpected internal fault: still never leak an exception to the UI.
        return fail("Could not evaluate that expression");
    }
}

function success(value) { return { ok: true, value: value, text: format(value) }; }

// Display text. Below 1e14 every digit of the plain form is genuine. From 1e14
// upward a plain integer would pad with zeros the double never held (2^60 is
// 1152921504606846976, kept as 1.1529215046068e+18), so switch to exponent
// form there. The text always re-parses to the same value.
var PLAIN_LIMIT = 1e14;
function format(value) {
    if (Math.abs(value) >= PLAIN_LIMIT) return value.toExponential();
    return String(value);
}
function fail(message) { return { ok: false, error: message }; }
function reject(message) { throw { calculator: true, message: message }; }

function run(text) {
    text = text.replace(/^[ \t\r\n]+|[ \t\r\n]+$/g, "");
    if (text.length === 0) reject("Enter an expression");
    if (text.length > MAX_LENGTH) reject("Expression is too long (limit " + MAX_LENGTH + " characters)");
    var tokens = tokenize(text);
    var state = { tokens: tokens, pos: 0, depth: 0 };
    var value = parseSum(state);
    if (state.pos < tokens.length) {
        var extra = tokens[state.pos];
        if (extra.type === "op" && extra.value === ")") reject("Unexpected ')' without a matching '('");
        reject("Unexpected '" + describe(extra) + "'; expected an operator");
    }
    return tidy(value);
}

function isDigit(c) { return c >= "0" && c <= "9"; }
function isOperator(c) { return c === "+" || c === "-" || c === "*" || c === "/" || c === "^" || c === "%" || c === "(" || c === ")"; }

function tokenize(text) {
    var out = [];
    var i = 0;
    while (i < text.length) {
        var c = text.charAt(i);
        if (c === " ") { i++; continue; }
        if (isDigit(c) || c === ".") {
            var start = i;
            while (i < text.length && isDigit(text.charAt(i))) i++;
            if (text.charAt(i) === ".") {
                i++;
                while (i < text.length && isDigit(text.charAt(i))) i++;
            }
            var literal = text.slice(start, i);
            if (literal === ".") reject("'.' is not a number");
            if (text.charAt(i) === ".") reject("Unexpected second '.' in number '" + literal + ".'");
            // Optional exponent: 1e5, 1.5E-3, 1e+301. Lets a displayed result be
            // typed or chained back in. Only the exponent marker is a letter; the
            // mantissa above is always at least one digit.
            if (text.charAt(i) === "e" || text.charAt(i) === "E") {
                i++;
                if (text.charAt(i) === "+" || text.charAt(i) === "-") i++;
                var digitsStart = i;
                while (i < text.length && isDigit(text.charAt(i))) i++;
                if (i === digitsStart) reject("Incomplete exponent in number '" + text.slice(start, i) + "'");
                literal = text.slice(start, i);
                if (text.charAt(i) === "." || text.charAt(i) === "e" || text.charAt(i) === "E") {
                    reject("Unexpected '" + text.charAt(i) + "' after exponent in number '" + literal + "'");
                }
            }
            var number = Number(literal);
            if (number === Infinity) reject("Number '" + literal + "' is too large");
            out.push({ type: "num", value: number, text: literal });
        } else if (isOperator(c)) {
            out.push({ type: "op", value: c, text: c });
            i++;
        } else {
            reject("Unsupported character '" + printable(c) + "'");
        }
        if (out.length > MAX_TOKENS) reject("Expression has too many terms (limit " + MAX_TOKENS + ")");
    }
    return out;
}

function printable(c) {
    var code = c.charCodeAt(0);
    if (code < 32 || code === 127) return "\\u" + ("000" + code.toString(16)).slice(-4);
    return c;
}

function describe(token) { return token.text; }

function parseSum(state) {
    var left = parseProduct(state);
    while (peek(state, "+") || peek(state, "-")) {
        var op = state.tokens[state.pos++].value;
        var right = parseProduct(state);
        left = op === "+" ? left + right : left - right;
        checkFinite(left);
    }
    return left;
}

function parseProduct(state) {
    var left = parseUnary(state);
    while (peek(state, "*") || peek(state, "/")) {
        var op = state.tokens[state.pos++].value;
        var right = parseUnary(state);
        if (op === "*") {
            left = left * right;
        } else {
            if (right === 0) reject("Cannot divide by zero");
            left = left / right;
        }
        checkFinite(left);
    }
    return left;
}

function parseUnary(state) {
    if (peek(state, "-") || peek(state, "+")) {
        var sign = state.tokens[state.pos++].value;
        enter(state);
        var operand = parseUnary(state);
        leave(state);
        return sign === "-" ? -operand : operand;
    }
    return parseExponent(state);
}

// Right associative: 2^3^2 is 2^(3^2). The exponent may carry its own sign.
function parseExponent(state) {
    var base = parsePostfix(state);
    if (peek(state, "^")) {
        state.pos++;
        enter(state);
        var power = parseUnary(state);
        leave(state);
        if (Math.abs(power) > MAX_EXPONENT) reject("Exponent is too large (limit " + MAX_EXPONENT + ")");
        if (base === 0 && power < 0) reject("Cannot divide by zero"); // 0^-n is 1/0^n
        var result = Math.pow(base, power);
        checkFinite(result); // also rejects NaN, e.g. (-8)^0.5
        return result;
    }
    return base;
}

// Postfix percent: x% is x/100, applied to the operand it follows.
function parsePostfix(state) {
    var value = parsePrimary(state);
    while (peek(state, "%")) {
        state.pos++;
        value = value / 100;
    }
    return value;
}

function parsePrimary(state) {
    var token = state.tokens[state.pos];
    if (!token) {
        reject(state.pos === 0 ? "Enter an expression" : "Incomplete expression; expected a number");
    }
    if (token.type === "num") {
        state.pos++;
        return token.value;
    }
    if (token.value === "(") {
        state.pos++;
        enter(state);
        if (peek(state, ")")) reject("Empty parentheses");
        var inner = parseSum(state);
        if (!peek(state, ")")) reject("Missing closing ')'");
        state.pos++;
        leave(state);
        return inner;
    }
    if (token.value === ")") reject("Unexpected ')' without a matching '('");
    reject("Unexpected '" + describe(token) + "'; expected a number");
}

function peek(state, op) {
    var t = state.tokens[state.pos];
    return !!t && t.type === "op" && t.value === op;
}

function enter(state) {
    state.depth++;
    if (state.depth > MAX_DEPTH) reject("Expression is nested too deeply (limit " + MAX_DEPTH + ")");
}
function leave(state) { state.depth--; }

function checkFinite(value) {
    if (value === Infinity || value === -Infinity) reject("Result is too large");
    if (value !== value) reject("Result is not a real number");
}

// Round away binary noise for display and for the returned value alike.
function tidy(value) {
    checkFinite(value);
    if (value === 0) return 0; // also folds -0
    var rounded = Number(value.toPrecision(SIGNIFICANT_DIGITS));
    checkFinite(rounded);
    return rounded;
}
