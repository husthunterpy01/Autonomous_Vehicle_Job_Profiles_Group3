"use client";

import Link from "next/link";
import {
  type KeyboardEvent as ReactKeyboardEvent,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";

export type ProfileDropdownUser = {
  displayName: string;
  avatarUrl?: string | null;
};

type ProfileDropdownProps = {
  user: ProfileDropdownUser;
  changeInformationHref: string;
  favoriteListHref: string;
  onLogout: () => void | Promise<void>;
  onOpen?: () => void;
};

const MENU_ITEM_COUNT = 3;

function getInitials(displayName: string) {
  const words = displayName.trim().split(/\s+/).filter(Boolean);

  if (words.length === 0) {
    return "U";
  }

  return words
    .slice(0, 2)
    .map((word) => word.charAt(0))
    .join("")
    .toUpperCase();
}

export default function ProfileDropdown({
  user,
  changeInformationHref,
  favoriteListHref,
  onLogout,
  onOpen,
}: ProfileDropdownProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const itemRefs = useRef<Array<HTMLElement | null>>([]);
  const initialFocusIndexRef = useRef(0);
  const triggerId = useId();
  const menuId = useId();
  const displayName = user.displayName.trim() || "your account";
  const initials = getInitials(user.displayName);

  function openMenu(initialFocusIndex = 0) {
    initialFocusIndexRef.current = initialFocusIndex;
    setOpen(true);
    onOpen?.();
  }

  function closeMenu({ returnFocus = false } = {}) {
    setOpen(false);

    if (returnFocus) {
      triggerRef.current?.focus();
    }
  }

  function moveFocus(currentIndex: number, direction: 1 | -1) {
    const nextIndex =
      (currentIndex + direction + itemRefs.current.length) %
      itemRefs.current.length;
    itemRefs.current[nextIndex]?.focus();
  }

  function handleTriggerKeyDown(event: ReactKeyboardEvent<HTMLButtonElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      openMenu(0);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      openMenu(MENU_ITEM_COUNT - 1);
    }
  }

  function handleItemKeyDown(
    event: ReactKeyboardEvent<HTMLElement>,
    index: number,
  ) {
    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        moveFocus(index, 1);
        break;
      case "ArrowUp":
        event.preventDefault();
        moveFocus(index, -1);
        break;
      case "Home":
        event.preventDefault();
        itemRefs.current[0]?.focus();
        break;
      case "End":
        event.preventDefault();
        itemRefs.current.at(-1)?.focus();
        break;
      case " ":
        if (event.currentTarget instanceof HTMLAnchorElement) {
          event.preventDefault();
          event.currentTarget.click();
        }
        break;
      case "Tab":
        closeMenu();
        break;
    }
  }

  useEffect(() => {
    if (!open) {
      return;
    }

    itemRefs.current[initialFocusIndexRef.current]?.focus();

    function handlePointerDown(event: PointerEvent) {
      if (
        event.target instanceof Node &&
        !containerRef.current?.contains(event.target)
      ) {
        setOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
        triggerRef.current?.focus();
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open]);

  return (
    <div ref={containerRef} className="relative shrink-0">
      <button
        ref={triggerRef}
        id={triggerId}
        type="button"
        aria-label={`Open profile menu for ${displayName}`}
        aria-controls={open ? menuId : undefined}
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => (open ? closeMenu() : openMenu())}
        onKeyDown={handleTriggerKeyDown}
        className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-full border border-line bg-primary-light text-sm font-semibold text-primary transition-colors hover:border-primary hover:bg-section focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
      >
        {user.avatarUrl ? (
          <span
            aria-hidden="true"
            className="h-full w-full bg-cover bg-center"
            style={{
              backgroundImage: `url(${JSON.stringify(user.avatarUrl)})`,
            }}
          />
        ) : (
          <span aria-hidden="true">{initials}</span>
        )}
      </button>

      {open && (
        <div
          id={menuId}
          role="menu"
          aria-labelledby={triggerId}
          className="absolute right-0 z-[60] mt-2 w-60 max-w-[calc(100vw-2rem)] rounded-xl border border-line bg-surface p-2 shadow-lg"
        >
          <p
            role="presentation"
            className="truncate border-b border-line px-3 pb-2 pt-1 text-xs font-medium text-ink-muted"
          >
            {displayName}
          </p>

          <Link
            ref={(element) => {
              itemRefs.current[0] = element;
            }}
            href={changeInformationHref}
            role="menuitem"
            tabIndex={-1}
            onClick={() => closeMenu()}
            onKeyDown={(event) => handleItemKeyDown(event, 0)}
            className="mt-1 flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium text-ink-secondary transition-colors hover:bg-section hover:text-ink focus:bg-primary-light focus:text-primary focus:outline-none"
          >
            <svg
              aria-hidden="true"
              className="h-4 w-4 shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.8}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15.232 5.232l3.536 3.536M9 11.25l6.879-6.879a2.121 2.121 0 013 3L12 14.25 8.25 15l.75-3.75zM6.75 6.75H5.25A2.25 2.25 0 003 9v9.75A2.25 2.25 0 005.25 21H15a2.25 2.25 0 002.25-2.25v-1.5"
              />
            </svg>
            Change Information
          </Link>

          <Link
            ref={(element) => {
              itemRefs.current[1] = element;
            }}
            href={favoriteListHref}
            role="menuitem"
            tabIndex={-1}
            onClick={() => closeMenu()}
            onKeyDown={(event) => handleItemKeyDown(event, 1)}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium text-ink-secondary transition-colors hover:bg-section hover:text-ink focus:bg-primary-light focus:text-primary focus:outline-none"
          >
            <svg
              aria-hidden="true"
              className="h-4 w-4 shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.8}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111 5.518.442c.499.04.701.663.321.988l-4.204 3.602 1.285 5.385a.562.562 0 01-.84.61L12 16.748l-4.725 2.889a.562.562 0 01-.84-.61l1.285-5.385-4.204-3.602a.562.562 0 01.321-.988l5.518-.442 2.125-5.111z"
              />
            </svg>
            My Favorite List
          </Link>

          <button
            ref={(element) => {
              itemRefs.current[2] = element;
            }}
            type="button"
            role="menuitem"
            tabIndex={-1}
            onClick={() => {
              closeMenu();
              void onLogout();
            }}
            onKeyDown={(event) => handleItemKeyDown(event, 2)}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium text-ink-secondary transition-colors hover:bg-section hover:text-ink focus:bg-primary-light focus:text-primary focus:outline-none"
          >
            <svg
              aria-hidden="true"
              className="h-4 w-4 shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.8}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3-3H9m9.75 0l-3-3m3 3l-3 3"
              />
            </svg>
            Log Out
          </button>
        </div>
      )}
    </div>
  );
}
