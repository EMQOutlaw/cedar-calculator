// node tests/core/calculator_engine_test.js components/CalculatorEngine.js
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const p={};vm.createContext(p);vm.runInContext(fs.readFileSync(process.argv[2],'utf8').replace('.pragma library',''),p);

function ok(expr,value,text){
    const r=p.evaluate(expr);
    const label='evaluate('+JSON.stringify(expr)+') -> '+JSON.stringify(r);
    assert.strictEqual(r.ok,true,label);
    assert.strictEqual(r.value,value,label);
    assert.strictEqual(r.text,text===undefined?String(value):text,label);
    assert.strictEqual(r.error,undefined,label);
    assert.deepStrictEqual(Object.keys(r).sort(),['ok','text','value'],label);
}
function bad(expr,pattern){
    const r=p.evaluate(expr);
    assert.strictEqual(r.ok,false,'expected failure for '+JSON.stringify(expr)+', got '+JSON.stringify(r));
    assert.strictEqual(typeof r.error,'string');
    assert.ok(r.error.length>0,'empty error for '+JSON.stringify(expr));
    assert.strictEqual(r.value,undefined,'failure must not carry value');
    if(pattern) assert.ok(pattern.test(r.error),JSON.stringify(expr)+': error '+JSON.stringify(r.error)+' !~ '+pattern);
}

// --- Cycle 1: contract and basic arithmetic
ok('1+2',3);
ok('7-10',-3);
ok('6*7',42);
ok('8/2',4);
ok(' 2 +  2 ',4);

// --- Cycle 2: precedence, parentheses, unary signs, decimals
ok('2+3*4',14);
ok('(2+3)*4',20);
ok('10-4-3',3);              // left associative
ok('100/10/2',5);
ok('((1+2))*((3))',9);
ok('-5',-5);
ok('+5',5);
ok('-(2+3)',-5);
ok('2*-3',-6);
ok('--4',4);
ok('-2*-2',4);
ok('1.5+2.25',3.75);
ok('.5+.5',1);
ok('3.',3);
ok('0.5*4',2);

// --- Cycle 3: postfix percent (x/100, not modulo) and ^ exponent
ok('50%',0.5);
ok('200*10%',20);
ok('7%%',0.0007);
ok('(20+30)%',0.5);
ok('-50%',-0.5);               // percent binds tighter than unary minus
ok('2^3',8);
ok('2^3^2',512);               // right associative: 2^(3^2)
ok('2*3^2',18);                // ^ above *
ok('(2*3)^2',36);
ok('-2^2',-4);                 // unary minus applies after ^ (like math notation)
ok('2^-1',0.5);                // sign allowed in exponent
ok('4^0.5',2);
ok('100%^2',1);                // percent binds tighter than ^
ok('9^50%',3);                 // percent applies to its own operand: 9^(0.5)

// --- Cycle 4: display precision (standard doubles, noise hidden)
ok('0.1+0.2',0.3,'0.3');
ok('0.1*3',0.3,'0.3');
ok('1.1*1.1',1.21,'1.21');
ok('3*1.1',3.3,'3.3');
ok('1/3',0.33333333333333,'0.33333333333333');
ok('2/3',0.66666666666667,'0.66666666666667');
ok('0*-1',0,'0');            // no "-0"
ok('123456789*1000',123456789000);                      // < 1e14 stays plain
ok('99999999999999',99999999999999,'99999999999999');   // 14 digits exactly: plain
ok('99999999999999+0.5',1e14,'1e+14');                 // 15 significant digits round to 1e14
ok('99999999999999+1',100000000000000,'1e+14');   // >= 1e14: exponent form, digits shown are all real
// Approximation behaviour pinned so docs stay truthful (standard doubles):
ok('0.1^400',0,'0');                                    // underflow quietly becomes 0
ok('1e-200*1e-200',0,'0');
ok('2^60',1.1529215046068e+18,'1.1529215046068e+18');   // true value 1152921504606846976: display rounds to 14 digits
ok('2^53+1',9.007199254741e+15,'9.007199254741e+15');   // beyond 2^53 integers are not exact
ok('123456789012345678',1.2345678901235e+17,'1.2345678901235e+17');
ok('0.1+0.2-0.3',5.5511151231258e-17,'5.5511151231258e-17'); // KNOWN LIMIT: cancellation residue is not hidden (no absolute epsilon, so 1e-300*1e-10 stays meaningful)
ok('(0.1+0.2)-0.3',5.5511151231258e-17,'5.5511151231258e-17');
ok('0.3-0.3',0,'0');
ok('1e15+0.3',1e15,'1e+15');                            // 0.3 lost at this magnitude; no fake trailing digits

// --- Cycle 5: friendly errors, never throw
function neverThrows(expr){
    let r;
    try{ r=p.evaluate(expr); }catch(e){ assert.fail('evaluate threw for '+JSON.stringify(expr)+': '+e); }
    assert.ok(r&&typeof r.ok==='boolean','no result for '+JSON.stringify(expr));
    return r;
}
bad('',/enter|empty/i);
bad('   ',/enter|empty/i);
bad(null,/enter|empty/i);
bad(undefined,/enter|empty/i);
bad('1/0',/divide|division|zero/i);
bad('1/(2-2)',/divide|division|zero/i);
bad('0/0',/divide|division|zero/i);
bad('0^-1',/divide by zero/i);                     // 0^-n is 1/0^n
bad('0^-2',/divide by zero/i);
bad('(1-1)^-0.5',/divide by zero/i);
bad('0^(-1)',/divide by zero/i);
bad('-0^-1',/divide by zero/i);
ok('0^0',1);                                       // Math.pow convention
ok('0^1',0);
ok('0^0.5',0);
bad('10^1000',/large|overflow|range/i);
bad('(-8)^0.5',/number|real|undefined/i);   // NaN -> friendly
bad('1+',/incomplete|expected|missing/i);
bad('*1',/unexpected|expected/i);
bad('2**3',/unexpected|expected/i);
bad('(1+2',/paren|\)|close/i);
bad('1+2)',/paren|\(|unexpected/i);
bad(')(',/paren|unexpected/i);
bad('()',/empty|expected|paren/i);
bad('1 2',/unexpected|operator/i);
bad('1..2',/number|unexpected/i);
bad('1.2.3',/number|unexpected/i);
bad('.',/number|unexpected/i);
bad('%',/unexpected|expected/i);
bad('2^',/incomplete|expected|missing/i);
bad('abc',/unexpected|character|unsupported/i);
bad('1f5',/unexpected|character|unsupported/i);           // only e/E marks an exponent
bad('0x10',/unexpected|character|unsupported/i);
bad('1_000',/unexpected|character|unsupported/i);
bad('1 + "2"',/unexpected|character|unsupported/i);

// --- Cycle 6: malicious / hostile input never escapes the arithmetic sandbox
const hostile=[
    'process.exit(1)','require("fs")','this.constructor.constructor("return 1")()',
    'globalThis','eval("1")','Function("return 1")()','__proto__','constructor',
    'Math.PI','1;2','1,2','a=1','[]+[]','{}','`1`','1/*x*/+1','1//1','\\u0031',
    'Infinity','NaN','1e309','new Array(1e9)','while(true){}',
    '1\n+1','1\t+1','\u0661+\u0661',  // newline/tab/Arabic-Indic digits are not whitespace or digits we accept
];
for(const h of hostile){ const r=neverThrows(h); assert.strictEqual(r.ok,false,'hostile accepted: '+JSON.stringify(h)+' -> '+JSON.stringify(r)); }
assert.strictEqual(typeof p.evaluate,'function');
neverThrows(12345); neverThrows({}); neverThrows([1,2]); neverThrows(true);
ok(12,12);                     // a bare number is stringified and evaluated
assert.strictEqual(p.evaluate({toString(){throw new Error('boom');}}).ok,false);

// --- Cycle 7: bounds (length, token count, nesting, exponent) and recovery
ok(' 1+1 ',2);
ok('\t1+1\n',2);                                   // outer whitespace trimmed
ok('1+'.repeat(60)+'1',61);                        // 121 chars / 121 tokens: within limits
bad('1+'.repeat(70)+'1',/too many|terms|limit/i);  // 141 tokens > 128
bad('1+'.repeat(200)+'1',/too long/i);            // 401 chars > 256 (length checked before tokens)
bad('1'.repeat(300),/too long/i);                  // one token, still too long
ok('1'.repeat(256),1.1111111111111e+255,'1.1111111111111e+255');   // exactly at the limit
bad('('.repeat(40)+'1'+')'.repeat(40),/nested|deep|limit/i);
ok('('.repeat(20)+'1'+')'.repeat(20),1);
bad('-'.repeat(60)+'1',/nested|deep|limit/i);      // chained signs count as depth
bad('2^2000',/exponent|large|limit/i);
bad('2^(-2000)',/exponent|large|limit/i);
ok('2^1000',1.0715086071863e+301,'1.0715086071863e+301');
bad('2^1000*2^1000',/too large|overflow/i);
ok('9'.repeat(200)+'*'+'9'.repeat(50),1e250,'1e+250');   // large but finite is fine
bad('10^300*10^300',/too large|overflow/i);
ok('(((((1+2)*3)-4)/5)^2)',1);
ok('1/3*3',1);                                     // 0.1+0.2 style noise does not survive tidy
bad('1/0+',/divide|zero|incomplete/i);             // first error wins or parse error; either is friendly
ok('2+2',4);                                       // recovery after error

// --- Cycle 8: scientific notation input (so results chain: "(1.07e+301)*2")
ok('1e5',100000);
ok('1E5',100000);
ok('1e+5',100000);
ok('1e-3',0.001);
ok('1.5e3',1500);
ok('.5e1',5);
ok('5.e1',50);
ok('2e3+1',2001);
ok('1e2^2',10000);                                 // literal binds before ^
ok('1e2%',1);
ok('-1e2',-100);
ok('1e-2-1e-2',0);
ok('1.0715086071863e+301*2',2.1430172143726e+301,'2.1430172143726e+301');
ok('(1.0715086071863e+301)*2',2.1430172143726e+301,'2.1430172143726e+301');
ok('1e-7*1',1e-7,'1e-7');
bad('1e',/incomplete exponent/i);
bad('1e+',/incomplete exponent/i);
bad('1e-',/incomplete exponent/i);
bad('e5',/unsupported|unexpected/i);
bad('1ee5',/exponent|number|unexpected/i);
bad('1e5e5',/exponent|number|unexpected/i);
bad('1e5.5',/number|unexpected/i);
bad('1e.5',/exponent|number|unexpected/i);
bad('1e5%5',/unexpected/i);
bad('1e400',/number '1e400' is too large/i);        // literal overflows a double: named in the message
bad('1e-400+1e400',/number '1e400' is too large/i);
bad('1e+-5',/exponent|number|unexpected/i);
bad('1e 5',/exponent|number|unexpected/i);
bad('1 e5',/unsupported|unexpected/i);
bad('1e99999999999999999999999',/number '1e9+' is too large/i);
bad('1e'+'0'.repeat(300),/too long/i);
ok('1e-400',0,'0');                                 // underflows to zero, finite

// Round trip: evaluate(result.text) must reproduce the value for any success.
for(const expr of ['2^1000','1/3','2/3','7%%','1e-7*1','0.1+0.2','123456789*1000','9'.repeat(200)+'*'+'9'.repeat(50),'2^-1000','-2^1000','1e-300*1e-10','(2^1000)*2']){
    const r=p.evaluate(expr); assert.strictEqual(r.ok,true,expr+': '+JSON.stringify(r));
    const again=p.evaluate(r.text); assert.strictEqual(again.ok,true,'roundtrip '+expr+' text '+r.text+': '+JSON.stringify(again));
    assert.strictEqual(again.value,r.value,'roundtrip value '+expr);
    assert.strictEqual(again.text,r.text,'roundtrip text '+expr);
    const chained=p.evaluate('('+r.text+')*1'); assert.strictEqual(chained.ok,true,'chained '+expr+': '+JSON.stringify(chained));
    assert.strictEqual(chained.value,r.value,'chained value '+expr);
}
// Deterministic fuzz (seeded LCG): every successful result round-trips and chains.
{
    let seed=20260101; const rnd=n=>{seed=(seed*1103515245+12345)&0x7fffffff; return seed%n;};
    const atoms=['0','1','2','3','7','10','0.1','0.5','2.5','100','1e3','1e-3','3.7e2','99999'];
    const ops=['+','-','*','/','^','*','+'];
    let successes=0;
    for(let n=0;n<2000;n++){
        let e=atoms[rnd(atoms.length)]; const terms=1+rnd(4);
        for(let t=0;t<terms;t++){ const op=ops[rnd(ops.length)]; let a=atoms[rnd(atoms.length)]; if(op==='^') a=String(rnd(5)); if(rnd(5)===0) a='-'+a; if(rnd(6)===0) a=a+'%'; e=(rnd(3)===0?'('+e+')':e)+op+a; }
        const r=neverThrows(e); if(!r.ok) continue; successes++;
        const again=neverThrows(r.text); assert.strictEqual(again.ok,true,'fuzz roundtrip '+e+' -> '+r.text+': '+JSON.stringify(again));
        assert.strictEqual(again.value,r.value,'fuzz roundtrip value '+e+' -> '+r.text);
        const chained=neverThrows('('+r.text+')*1'); assert.strictEqual(chained.value,r.value,'fuzz chained '+e+' -> '+r.text);
    }
    assert.ok(successes>1000,'fuzz produced too few successes: '+successes);
}

console.log('PASS: CalculatorEngine');
