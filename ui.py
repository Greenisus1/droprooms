import curses,os

def put(screen,y,x,text,attr=0):
 h,w=screen.getmaxyx()
 if 0<=y<h and 0<=x<w:
  try:screen.addnstr(y,x,str(text),max(0,w-x-1),attr)
  except curses.error:pass

def run(loop):
 if not os.isatty(0) or not os.isatty(1):print('Use an interactive terminal.');return 1
 try:
  def main(screen):
   screen.keypad(True)
   try:curses.curs_set(0)
   except curses.error:pass
   return loop(screen)
  curses.wrapper(main);return 0
 except KeyboardInterrupt:return 0
 except curses.error as exc:print('Terminal stopped:',exc);return 1
