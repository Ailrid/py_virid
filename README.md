# virid

## [中文说明](README.zh.md)

`virid` is a deterministic, message-driven engine designed for heavy Electron applications, built with `TypeScript`. It completely decouples business logic from the clutter of UI frameworks, establishing a micro-distributed core with location transparency.

This repository is the `Python` port of `virid` (**Work in Progress**), aimed at providing strong determinism, synchronization, and decoupled state management and control tools for chaotic Python control flows.

## Modules

| **Module**     | **Position**     | **Key Features**                                             | Install                |
| -------------- | ---------------- | ------------------------------------------------------------ | ---------------------- |
| **virid.core** | Core             | Deterministic Tick mechanism, dual-buffered message pool, Dependency Injection (DI). | pip install virid-core |
| **virid.std**  | Core Enhancement | Provides message transactions, timing/sequence control, etc. | pip install virid-std  |

## 其他

👉 **[Virid Repository](https://github.com/Ailrid/virid)** – The complete virid framework written in TypeScript.
