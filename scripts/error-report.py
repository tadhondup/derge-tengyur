#!/usr/bin/env python3

# The MIT License (MIT)
# Copyright (c) 2018 Esukhia
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

import re
import os
import glob

PAREN_RE = re.compile(r"\(([^\),]*),([^\),]*)\)")

def parrepl(match, mode, filelinenum):
    first = match.group(1)
    sec = match.group(2)
    if (len(first) > 0 and len(sec) > 0 and (
            (first[0]== '་' and sec[0]!= '་') or 
            (sec[0]== '་' and first[0]!= '་') or
            (first[-1]== '་' and sec[-1]!= '་') or
            (sec[-1]== '་' and first[-1]!= '་'))):
        printerror("error on line "+str(filelinenum)+" tsheg not matching in parenthesis")
    return mode == 'first' and first or sec

error_regexps = [
        {"reg": re.compile(r"([^ །\(\[,]།[^ །\]\)༽,]|(?:[^ངོེིུ]|ང[^ངོེིུ]|[^ང][ོེིུ])་།|(?:[^ཀགཤ།ོེིུ]|[ཀགཤ][^ཀགཤོེིུ]|[^ཀགཤ][ོེིུ]|[ཀགཤ][ོེིུ]།+)། །།|།།།)"), "msg": "invalid shad sequence", "type": "punctuation"},
        {"reg": re.compile(r"[^ཀ-ྼ][ཱ-྄྆྇ྍ-ྼ]"), "msg": "invalid unicode combination sequence", "type": "invalid"},
        {"reg": re.compile(r"[^ༀ-࿚#-~ \[\]\{\}\.]"), "msg": "invalid unicode characters (non-Tibetan, non-ascii)", "type": "invalid"},
        {"reg": re.compile(r"([ྱུྲཿཾ྄ྃྭིྀ་ ])\1"), "msg": "invalid double diactitic sign (shabkyu, gigu, etc.)", "type": "invalid"},
        {"reg": re.compile(r"[ༀ-༃༆-༊༎-༟]"), "msg": "suspicious Tibetan character", "type": "invalid"},
        {"reg": re.compile(r"([ཱ-྇][ྍ-ྼ]|[ི-྄]ཱ|[ྃཾཿ][ཱ-ཽྀ])"), "msg": "invalid character order (vowel before subscript)", "type": "invalid"},
        {"reg": re.compile(r"(ཪ[ླྙྲྱཱ-྇ །་])"), "msg": "wrong form of rago used (0F62 vs. 0F65)", "type": "invalid"},
        {"reg": re.compile(r"([ཀགཤ།] །|[^ ཀགཤ།]། |[ཀགཤ།]། |[ཀགཤ།][། ]|[༽ཿ་ \]nl])$"), "msg": "invalid end of line", "type": "punctuation", "neg": True},
        {"reg": re.compile(r"([ཱེཻོཽ])\1"), "msg": "invalid vowel duplication (use 0F7D and 0F7B when relevant)", "type": "invalid"},
    ]

def check_simple_regexp(line, pagelinenum, filelinenum, volnum, options, shortfilename):
    for regex_info in error_regexps:
        if "neg" in regex_info and regex_info["reg"]:
            if not regex_info["reg"].search(line):
                report_error(pagelinenum, filelinenum, volnum, shortfilename, regex_info["type"], regex_info["msg"], "")
            continue
        for match in regex_info["reg"].finditer(line):
            s = match.start()
            e = match.end()
            linewithhighlight = line[:s]+"**"+line[s:e]+"**"+line[e:]
            report_error(pagelinenum, filelinenum, volnum, shortfilename, regex_info["type"], regex_info["msg"], linewithhighlight)

def report_error(linestr, filelinenum, volnum, shortfilename, errortype, errorstr, linewithhighlight):
    printerror(shortfilename+", l. "+str(filelinenum)+" ("+linestr+"): "+errortype+": "+errorstr)
    if len(linewithhighlight) > 1:
        printerror("  -> "+linewithhighlight)

def parse_one_line(line, filelinenum, state, volnum, options, shortfilename):
    if filelinenum == 1:
        state['pageseqnum']= 1
        state['pagenum']= 1
        state['pageside']= 'a'
        return
    pagelinenum = ''
    endpnumi = line.find(']')
    if endpnumi == -1:
        report_error("", filelinenum, volnum, shortfilename, "format", "cannot find \"]\"", "")
        return
    pagelinenum = line[1:endpnumi]
    if len(pagelinenum) < 2:
        report_error("", filelinenum, volnum, shortfilename, "format", "cannot understand page indication \"["+pagelinenum+"]\"", "")
        return
    pagenum = -1
    pageside = -1
    linenum = 0
    isBis = False
    doti = pagelinenum.find('.')
    if doti == -1:
        pageside = pagelinenum[-1]
        if pageside not in ['a', 'b']:
            report_error(pagelinenum, filelinenum, volnum, shortfilename, "format", "cannot understand page side", "")
            return
        pagenumstr = pagelinenum[:-1]
        if pagelinenum[-2]== 'x':
            isBis = True
            pagenumstr = pagelinenum[:-2]
        try:
            pagenum = int(pagenumstr)
        except ValueError:
            report_error(pagelinenum, filelinenum, volnum, shortfilename, "format", "cannot convert page to integer", "")
            return
    else:
        linenumstr = pagelinenum[doti+1:]
        pageside = pagelinenum[doti-1]
        if pageside not in ['a', 'b']:
            report_error(pagelinenum, filelinenum, volnum, shortfilename, "format", "cannot understand page side", "")
            return
        pagenumstr = pagelinenum[0:doti-1]
        if pagelinenum[doti-2]== 'x':
            isBis = True
            pagenumstr = pagelinenum[0:doti-2]
        try: 
            pagenum = int(pagenumstr)
            linenum = int(linenumstr)
        except ValueError:
            report_error(pagelinenum, filelinenum, volnum, shortfilename, "format", "cannot convert page / line to integer", "")
            return
    newpage = False
    if 'pagenum' in state and 'pageside' in state:
        oldpagenum = state['pagenum']
        oldpageside = state['pageside']
        if oldpagenum != pagenum and oldpagenum != pagenum-1:
            report_error("", filelinenum, volnum, shortfilename, "pagenumbering", "leap in page numbers from "+str(oldpagenum)+" to "+str(pagenum), "")
        if oldpagenum == pagenum and oldpageside == 'b' and pageside == 'a':
            report_error("", filelinenum, volnum, shortfilename, "pagenumbering", "going backward in page sides", "")
        if oldpagenum == pagenum-1 and (pageside == 'b' or oldpageside == 'a'):
            report_error("", filelinenum, volnum, shortfilename, "pagenumbering", "leap in page sides", "")
        if oldpagenum != pagenum or oldpageside != pageside:
            newpage = True
    if newpage:
        state['pageseqnum']+= 1
    state['pagenum']= pagenum
    state['pageside']= pageside
    if 'linenum' in state and linenum != 0:
        oldlinenum = state['linenum']
        if oldlinenum != linenum and oldlinenum != linenum-1:
            report_error(pagelinenum, filelinenum, volnum, shortfilename, "pagenumbering", "leap in line numbers from "+str(oldlinenum)+" to "+str(linenum), "")
    state['linenum']= linenum
    check_simple_regexp(line, pagelinenum, filelinenum, volnum, options, shortfilename)
    text = ''
    if len(line) > endpnumi+1:
        text = line[endpnumi+1:]
        if '{T' in text:
            if not '}' in text:
                report_error(pagelinenum, filelinenum, volnum, shortfilename, "format", "missing closing \"}\"", "")
            closeidx = text.find('}')
            if not text.startswith('༄༅༅། །', closeidx+1):
                rightcontext = text[closeidx+1:closeidx+5]
                report_error(pagelinenum, filelinenum, volnum, shortfilename, "punctuation", "possible wrong beginning of text: \""+rightcontext+"\" should be \"༄༅༅། །\"", "")
            locstr = str(pagenum)+pageside+str(linenum)+" ("+str(volnum)+")"
        if 'keep_errors_indications' not in options or not options['keep_errors_indications']:
            text = text.replace('[', '').replace(']', '')
        if 'fix_errors' not in options or not options['fix_errors']:
            text = re.sub(r"\(([^\),]*),([^\),]*)\)", lambda m: parrepl(m, 'first', filelinenum), text)
        else:
            text = re.sub(r"\(([^\),]*),([^\),]*)\)", lambda m: parrepl(m, 'second', filelinenum), text)
        if text.find('(') != -1 or text.find(')') != -1:
            report_error(pagelinenum, filelinenum, volnum, shortfilename, "format", "spurious parenthesis", "")

def parse_one_file(infilename, volnum, options, shortfilename):
    with open(infilename, 'r', encoding="utf-8") as inf:
        state = {}
        linenum = 1
        for line in inf:
            if linenum == 1:
                line = line[1:]# remove BOM
            # [:-1]to remove final line break
            parse_one_line(line[:-1], linenum, state, volnum, options, shortfilename)
            linenum += 1

errfile = open("errors.txt","w")

def printerror(err):
    errfile.write(err+"\n")

if __name__ == '__main__':
    """ Example use """
    options = {
        "fix_errors": False,
        "keep_errors_indications": False
    }
    for infilename in sorted(glob.glob("../derge-tengyur-tags/*.txt")):
        #print(infilename)
        volnum = int(infilename[22:25])
        shortfilename = infilename[22:-4]
        parse_one_file(infilename, volnum, options, shortfilename)

errfile.close()