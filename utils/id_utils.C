/*
 *
 * Copyright (C) 2000 Frans Kaashoek (kaashoek@lcs.mit.edu)
 * Copyright (C) 2001 Frans Kaashoek (kaashoek@lcs.mit.edu) and 
 *                    Frank Dabek (fdabek@lcs.mit.edu).
 *
 *  Permission is hereby granted, free of charge, to any person obtaining
 *  a copy of this software and associated documentation files (the
 *  "Software"), to deal in the Software without restriction, including
 *  without limitation the rights to use, copy, modify, merge, publish,
 *  distribute, sublicense, and/or sell copies of the Software, and to
 *  permit persons to whom the Software is furnished to do so, subject to
 *  the following conditions:
 *
 *  The above copyright notice and this permission notice shall be
 *  included in all copies or substantial portions of the Software.
 *
 *  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 *  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 *  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 *  NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
 *  LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 *  OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
 *  WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 *
 */

#include <assert.h>
#include "id_utils.h"

chordID
incID (const chordID &n)
{
  chordID s = n + 1;
  chordID b (1);
  b = b << NBIT;
  if (s >= b)
    return s - b;
  else
    return s;
}

chordID
decID (const chordID &n)
{
  chordID p = n - 1;
  chordID b (1);
  b = (b << NBIT) - 1;
  p = p & b;
  return p;
}

chordID
successorID (const chordID &n, int p)
{
  chordID s;
  chordID t (1);
  chordID b (1);
  
  b = (b << NBIT) - 1;
  s = n;
  chordID t1 = t << p;
  s = s + t1;
  s = s & b;
  return s;
}

chordID
predecessorID (const chordID &n, int p)
{
  chordID s;
  chordID t (1);
  chordID b (1);
  
  b = (b << NBIT) - 1;
  s = n;
  chordID t1 = t << p;
  s = s - t1;
  s = s & b;
  return s;
}

chordID
doubleID (const chordID &n, int logbase)
{
  chordID s;
  chordID b (1);
  
  b = (b << NBIT) - 1;
  s = n << logbase;
  s = s & b;
  return s;
}

// Check whether n in (a,b) on the circle.
bool
between (const chordID &a, const chordID &b, const chordID &n)
{
  bool r;
  if (a == b) {
    r = n != a;   // n is the only node not in the interval (n,n)
  } else if (a < b) {
    r = (n > a) && (n < b);
  } else {
    r = (n > a) || (n < b);
  }
  return r;
}

// Check whether n in [a,b) on the circle.
bool
betweenleftincl (const chordID &a, const chordID &b, const chordID &n)
{
  bool r;
  if ((a == b) && (n == a)) {
    r = 1;
  } else if (a < b) {
    r = (n >= a) && (n < b);
  } else {
    r = (n >= a) || (n < b);
  }
  return r;
}

// Check whether n in (a,b] on the circle.
bool
betweenrightincl (const chordID &a, const chordID &b, const chordID &n)
{
  bool r;
  if ((a == b) && (n == a)) {
    r = 1;
  } else if (a < b) {
    r = (n > a) && (n <= b);
  } else {
    r = (n > a) || (n <= b);
  }
  return r;
}

// Check whether n in [a,b] on the circle.
bool
betweenbothincl (const chordID &a, const chordID &b, const chordID &n)
{
  bool r;
  if ((a == b) && (n == a)) {
    r = 1;
  } else if (a < b) {
    r = (n >= a) && (n <= b);
  } else {
    r = (n >= a) || (n <= b);
  }
  return r;
}
 

chordID
distance(const chordID &a, const chordID &b) 
{
  if (a < b) return (b - a);
  else {
    bigint t = bigint(1) << NBIT;
    return (t - a) + b;
  }
}

chordID
diff (const chordID &a, const chordID &b)
{
  chordID diff = (b - a);
  if (diff > 0) return diff;
  else return (bigint(1) << NBIT) - diff;
}

u_long
topbits (u_long n, const chordID &a)
{
  if (a == 0) return 0;

  assert (n <= 32);
  assert (n <= a.nbits ());
  u_long m = NBIT - a.nbits ();
  u_long r = 0;
  m = MIN (m, n);
  n = n - m;
  if (n > 0) {
    chordID x = a >> (a.nbits() - n);
    r = x.getui ();
  }
  return r;
}


chordID
shifttopbitout (u_long n, const chordID &a)
{
  if (a == 0) return a;

  chordID r = a;
  chordID mask = 1;
  mask = (mask << (NBIT - n)) - 1;
  r = r & mask;
  r = r << n;
  //  warnx << "shifttopbit " << n << " : a(" << a.nbits() << ") " << a 
  // << " r(" << r.nbits() << ") " << r << "\n";
  return r;
}

u_long
n1bits (u_long n)
{
  u_long t = 0;
  for (int i = 0; i < 32; i++) {
    if (0x1 & n) t++;
    n = n >> 1;
  }
  return t;
}

int 
bitindexmismatch (chordID n, chordID p)
{
  int bm;

  if (n.nbits () != p.nbits ()) {
    bm = p.nbits() - 1;
  } else {
    for (bm = p.nbits () - 1; bm >= 0; bm--) {
      if (n.getbit (bm) != p.getbit (bm))
	break;
    }
  }
  return bm;
}

int
bitindexzeros (chordID p, int i, int nzero)
{
  int c = 0;
  int b0;

  for (b0 = i; b0 >= 0; b0--) {
    if (p.getbit (b0) == 0) {
      c++;
      if (c >= nzero) break;
    } else {
      c = 0;
    }
  }
  return b0;
}

chordID
createbits (chordID n, int pos, chordID x)
{
  chordID mask = 1;
  int b0x = NBIT - x.nbits ();
  mask = (mask << ((n.nbits () - pos))) - 1;
  mask = mask << (pos + 1);
  chordID r = n & mask;
  chordID xtop = x >> (x.nbits () - (pos + 1 - b0x));
  r = r | xtop;
  return r;
}

u_long
log2 (u_long n)
{
  u_long l = 0;
  for (int i = 0; i < 32; i++) {
    if (0x1 & n) l = i;
    n = n >> 1;
  }
  return l;
}

bool
str2chordID (str c, chordID &newID)
{
  if (c.len () > NBIT / 4)
    return false;
  
  newID = 0;
  for (unsigned int i = 0; i < c.len (); i++) {
    if (c[i] >= '0' && c[i] <= '9') {
      newID = (newID << 4) | (c[i] - '0');
    } else if (c[i] >= 'a' && c[i] <= 'f') {
      newID = (newID << 4) | (c[i] - 'a' + 10);
    } else {
      return false;
    }
  }
  return true;
}