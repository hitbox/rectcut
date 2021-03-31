import abc
import argparse
import contextlib
import enum
import itertools
import os

with contextlib.redirect_stdout(open(os.devnull, 'w')):
    import pygame

def quit():
    pygame.event.post(pygame.event.Event(pygame.QUIT))

def connect_events(obj, prefix='on_'):
    """
    Return dictionary of event callbacks by inspecting `obj` for methods with
    `prefix`.
    """
    callbacks = {}
    for name in dir(obj):
        if name.startswith(prefix):
            event_name = name[len(prefix):].upper()
            event = getattr(pygame, event_name)
            callbacks[event] = getattr(obj, name)
    return callbacks

class EngineError(Exception):
    pass


class Cut(enum.Enum):

    VERTICAL = 0
    HORIZONTAL = 1


class ToolBase(metaclass=abc.ABCMeta):
    pass


class RectCutTool(ToolBase):

    def __init__(self):
        pass


class Display:

    def __init__(self, screensize, modeargs=None):
        self.screensize = screensize
        self.modeargs = modeargs
        if self.modeargs is None:
            self.modeargs = dict()
        self._surface = pygame.display.set_mode(self.screensize, **self.modeargs)
        self._initial = self._surface.copy()

    @property
    def surface(self):
        return self._surface

    def toscreen(self, x, y):
        return (x, y)

    def tospace(self, x, y):
        return (x, y)

    def clear(self):
        self._surface.blit(self._initial, (0,0))

    def update(self):
        pygame.display.flip()


class ScaledDisplay(Display):

    def __init__(self, screensize, buffersize, modeargs=None):
        super().__init__(screensize, modeargs)
        self.buffersize = buffersize
        self._buffer = pygame.Surface(self.buffersize)
        self._buffer_initial = self._buffer.copy()

        sw, sh = screensize
        bw, bh = buffersize
        self.xscale = sw // bw
        self.yscale = sh // bh

    @property
    def surface(self):
        return self._buffer

    def tospace(self, x, y):
        return (x // self.xscale, y // self.yscale)

    def toscreen(self, x, y):
        raise NotImplementedError
        return (x, y)

    def clear(self):
        self._buffer.blit(self._buffer_initial, (0, 0))

    def update(self):
        pygame.transform.scale(self._buffer, self.screensize, self._surface)
        pygame.display.flip()


class BaseState(metaclass=abc.ABCMeta):
    """
    Must inherit this to be run by an engine. Optional
    `Engine.event_handler_attribute` attribute is called to display all events
    except `pygame.QUIT`.
    """

    @abc.abstractmethod
    def update(self, elapsed):
        pass


class Engine:
    """
    Engine runs a state.
    """

    event_handler_attribute = 'event_handlers'

    def __init__(self, clock, screen, framerate=60):
        self.clock = clock
        self.screen = screen
        self.framerate = framerate
        self.running = False

    def run(self, state):
        self.running = True
        while self.running:
            self.update(state)

    def update(self, state):
        event_handlers = getattr(state, self.event_handler_attribute, {})
        elapsed = self.clock.tick(self.framerate)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type in event_handlers:
                event_handlers[event.type](event)
        self.screen.clear()
        state.update(elapsed)
        self.screen.update()


def cutrect(rect, slicedir, pos):
    "Cut rect returning two"
    x, y = pos
    if slicedir == Cut.VERTICAL:
        a = pygame.Rect(rect.left, rect.top, x - rect.left, rect.height)
        b = pygame.Rect(x, rect.top, rect.right - x, rect.height)
    elif slicedir == Cut.HORIZONTAL:
        a = pygame.Rect(rect.left, rect.top, rect.width, y - rect.top)
        b = pygame.Rect(rect.left, y, rect.width, rect.bottom - y)
    return (a, b)

def cutrectline(rect, slicedir, pos):
    "Preview line"
    x, y = pos
    if slicedir == Cut.VERTICAL:
        start, end = ((x, rect.top), (x, rect.bottom-1))
    elif slicedir == Cut.HORIZONTAL:
        start, end = ((rect.left, y), (rect.right-1, y))
    return start, end

class RectAttr:

    def __init__(self, rect, attribute):
        self.rect = rect
        self.attribute = attribute

    def collideattr(self, value):
        return getattr(self.rect, self.attribute) == value

    @property
    def value(self):
        if self.attribute == 'right':
            return getattr(self.rect, 'width')
        elif self.attribute == 'left':
            return getattr(self.rect, 'left')

    @value.setter
    def value(self, value):
        if self.attribute == 'right':
            self.rect.width = value
        elif self.attribute == 'left':
            diff = self.rect.left - value
            self.rect.left = value
            self.rect.width += diff


class RectLink:

    def __init__(self, rectattr1, rectattr2, concerning):
        self.rectattr1 = rectattr1
        self.rectattr2 = rectattr2
        self.concerning = concerning

    def collideattr(self, value):
        return self.rectattr1.collideattr(value) or self.rectattr2.collideattr(value)


class Rects:

    def __init__(self, *rects):
        self.rects = list(rects)
        self.preview = None
        self.slicedirs = itertools.cycle(Cut)
        self.slicedir = next(self.slicedirs)

    def cutrect(self, pos):
        x, y = map(int, pos)
        cut = None
        for rect in self.rects:
            if rect.collidepoint((x,y)):
                if x in (rect.left, rect.right-1):
                    # possible drag
                    pass
                elif y in (rect.top, rect.bottom-1):
                    # possible drag
                    pass
                else:
                    cut = rect
                    break
        if cut:
            self.rects.remove(cut)
            a, b = cutrect(cut, self.slicedir, pos)
            self.rects.append(a)
            self.rects.append(b)

    def update_preview(self, pos):
        x, y = map(int, pos)
        for rect in self.rects:
            if rect.collidepoint(pos):
                # NOTE: the right and bottom of a Rect is one pixel beyond
                # where the rect is drawn.
                if x in (rect.left, rect.right-1):
                    # possible drag
                    pass
                elif y in (rect.top, rect.bottom-1):
                    # possible drag
                    pass
                else:
                    self.preview = cutrectline(rect, self.slicedir, pos)
                    break
        else:
            self.preview = None

    def switchdir(self):
        self.slicedir = next(self.slicedirs)


class RectCutState(BaseState):
    """
    Demo cutting one big rect into littler ones.
    """

    def __init__(self, engine, initial_rect):
        self.engine = engine
        self.initial_rect = initial_rect
        self.rects = Rects(self.initial_rect)
        self.event_handlers = connect_events(self)

    def on_keydown(self, event):
        if event.key in (pygame.K_ESCAPE, pygame.K_q):
            quit()

    def on_mousebuttondown(self, event):
        if event.button == pygame.BUTTON_LEFT:
            pos = self.engine.screen.tospace(*event.pos)
            self.rects.cutrect(pos)
        elif event.button == pygame.BUTTON_RIGHT:
            self.rects.switchdir()
            pos = self.engine.screen.tospace(*event.pos)
            self.rects.update_preview(pos)

    def on_mousemotion(self, event):
        pos = self.engine.screen.tospace(*event.pos)
        self.rects.update_preview(pos)
        # XXX
        # Left off here thinking about dragging again. Want to drag "connected"
        # rects too.

    def update(self, elapsed):
        screen = self.engine.screen
        screen.clear()
        # draw all rects
        for rect in self.rects.rects:
            pygame.draw.rect(screen.surface, (200,200,200), rect, 1)
        # draw cut preview
        if self.rects.preview:
            a, b = self.rects.preview
            pygame.draw.line(screen.surface, (200,0,0), a, b)
        screen.update()


def run():
    pygame.display.init()

    rect = pygame.Rect(0, 0, 100, 100)

    screen = ScaledDisplay((8*rect.width, 8*rect.height), rect.size)
    #screen = Display(rect.size)

    clock = pygame.time.Clock()
    engine = Engine(clock, screen)

    initial_rect = rect.inflate(-rect.width*.25, -rect.width*.25)
    state = RectCutState(engine, initial_rect)

    engine.run(state)

def main(argv=None):
    """
    https://halt.software/dead-simple-layouts/
    """
    parser = argparse.ArgumentParser(description=main.__doc__)
    args = parser.parse_args(argv)
    run()

if __name__ == '__main__':
    main()
