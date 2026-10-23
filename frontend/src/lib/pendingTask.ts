// A task typed into the website demo, carried through sign-up so the
// builder can start from it. Session storage: it never leaves this tab.

const KEY = "autoflow.pendingTask";

export function savePendingTask(task: string) {
  try {
    window.sessionStorage.setItem(KEY, task.slice(0, 2000));
  } catch {
    // storage unavailable: the user retypes the task after signing up
  }
}

export function peekPendingTask(): string {
  try {
    return window.sessionStorage.getItem(KEY) ?? "";
  } catch {
    return "";
  }
}

export function clearPendingTask() {
  try {
    window.sessionStorage.removeItem(KEY);
  } catch {
    // nothing stored
  }
}
