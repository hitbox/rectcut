import argparse
import contextlib
import itertools
import os

with contextlib.redirect_stdout(open(os.devnull, 'w')):
    import pygame

def cutrect(rect, slicedir, pos):
    "Cut rect returning two"
    x, y = pos
    if slicedir == 'v':
        a = pygame.Rect(rect.left, rect.top, x - rect.left, rect.height)
        b = pygame.Rect(x, rect.top, rect.right - x, rect.height)
    elif slicedir == 'h':
        a = pygame.Rect(rect.left, rect.top, rect.width, y - rect.top)
        b = pygame.Rect(rect.left, y, rect.width, rect.bottom - y)
    return (a, b)

def cutrectline(rect, slicedir, pos):
    "Preview line"
    x, y = pos
    if slicedir == 'v':
        return ((x, rect.top), (x, rect.bottom-1))
    elif slicedir == 'h':
        return ((rect.left, y), (rect.right-1, y))

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
        # XXX
        # Left off here trying to do the linked rect dragging thing.
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

    def __init__(self, rect):
        self.rects = [rect]
        self.preview = None
        self.slicedirs = itertools.cycle('vh')
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


def run_cutrect():
    # NOTE
    # 1. messed up for small rects
    # 2. loses a pixel on the right and bottom some times.
    SCREENSIZE = (800, 800)
    BUFFSIZE = (200, 200)
    pygame.display.init()
    pygame.font.init()
    screen = pygame.display.set_mode(SCREENSIZE)
    buffer = pygame.Surface(BUFFSIZE)
    xscale = screen.get_rect().width // buffer.get_rect().width
    yscale = screen.get_rect().height // buffer.get_rect().height
    clock = pygame.time.Clock()
    rects = Rects(buffer.get_rect().inflate(
        -buffer.get_rect().width*.25,
        -buffer.get_rect().width*.25))
    font = pygame.font.Font(None, 16)
    mouseposimage = pygame.Surface((0,0))
    running = True
    while running:
        elapsed = clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    x, y = event.pos
                    x //= xscale
                    y //= yscale
                    rects.cutrect((x, y))
                elif event.button == 3:
                    rects.switchdir()
                    x, y = event.pos
                    x //= xscale
                    y //= yscale
                    rects.update_preview((x, y))
            elif event.type == pygame.MOUSEMOTION:
                mouseposimage = font.render(f'{event.pos}', True, (200,200,200))
                x, y = event.pos
                x //= xscale
                y //= yscale
                rects.update_preview((x, y))
        buffer.fill((0,0,0))
        # draw all rects
        for rect in rects.rects:
            pygame.draw.rect(buffer, (200,200,200), rect, 1)
        # draw cut preview
        if rects.preview:
            pygame.draw.line(buffer, (200,0,0), rects.preview[0], rects.preview[1])
        # draw mouse position image
        x, y = pygame.mouse.get_pos()
        x //= xscale
        y //= yscale
        buffer.blit(mouseposimage, (x, y))
        # finalize draw
        pygame.transform.scale(buffer, screen.get_rect().size, screen)
        pygame.display.flip()

def run_drag():
    pygame.display.init()
    clock = pygame.time.Clock()
    screen = pygame.display.set_mode((600,600))
    rect = screen.get_rect()
    rect = rect.inflate(-rect.width * .25, -rect.height * .25)
    rect1, rect2 = cutrect(rect, 'v', rect.center)
    rectlink = RectLink(RectAttr(rect1, 'right'), RectAttr(rect2, 'left'), 'x')
    drag = None
    running = True
    while running:
        elapsed = clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
            elif event.type == pygame.MOUSEMOTION:
                x, y = event.pos
                if drag and drag.concerning == 'x':
                    drag.rectattr1.value += event.rel[0]
                    drag.rectattr2.value += event.rel[0]
                else:
                    if rectlink.concerning == 'x' and rectlink.collideattr(x):
                        pygame.mouse.set_system_cursor(pygame.SYSTEM_CURSOR_SIZEWE)
                    else:
                        pygame.mouse.set_system_cursor(pygame.SYSTEM_CURSOR_ARROW)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                if rectlink.collideattr(x):
                    drag = rectlink
                elif rectlink.collideattr(y):
                    drag = rectlink
            elif event.type == pygame.MOUSEBUTTONUP:
                drag = None

        screen.fill((0,0,0))
        pygame.draw.rect(screen, (200,)*3, rect1)
        pygame.draw.rect(screen, (200,)*3, rect2)
        pygame.draw.rect(screen, (200,50,50), rect1, 1)
        pygame.draw.rect(screen, (50,200,50), rect2, 1)
        pygame.display.flip()

def main(argv=None):
    """
    https://halt.software/dead-simple-layouts/
    """
    parser = argparse.ArgumentParser(description=main.__doc__)
    args = parser.parse_args(argv)

    #run_cutrect()
    run_drag()

if __name__ == '__main__':
    main()
