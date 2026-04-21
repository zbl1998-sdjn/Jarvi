import type { ReactNode } from 'react';

type OverlayDrawerSide = 'left' | 'right';

interface OverlayDrawerProps {
  open: boolean;
  side: OverlayDrawerSide;
  title: string;
  onClose: () => void;
  children: ReactNode;
}

export function OverlayDrawer({ open, side, title, onClose, children }: OverlayDrawerProps) {
  return (
    <>
      {open ? (
        <div
          aria-hidden="true"
          className="overlay-drawer__scrim"
          onClick={onClose}
          role="presentation"
        />
      ) : null}
      <aside
        aria-hidden={open ? 'false' : 'true'}
        aria-label={title}
        className={`overlay-drawer overlay-drawer--${side}${open ? ' overlay-drawer--open' : ''}`}
        role="dialog"
      >
        <header className="overlay-drawer__header">
          <h2 className="overlay-drawer__title">{title}</h2>
          <button
            aria-label="关闭抽屉"
            className="overlay-drawer__close"
            onClick={onClose}
            type="button"
          >
            收起
          </button>
        </header>
        <div className="overlay-drawer__body">{children}</div>
      </aside>
    </>
  );
}
