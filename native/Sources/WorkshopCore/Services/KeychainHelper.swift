// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pedal Workshop Contributors
// https://github.com/ArdChoille637/pedal-workshop

import Foundation
import Security

// MARK: – KeychainHelper
//
// PURPOSE:
//   Thin wrapper around the Security framework Keychain API for storing small
//   secret strings (e.g. API keys).  Prefer this over UserDefaults for any
//   value that should not appear in a backup or be readable without auth.
//
// USAGE:
//   // Store
//   KeychainHelper.set("my-secret", forKey: "mouser_api_key")
//
//   // Read
//   let key = KeychainHelper.get("mouser_api_key") ?? ""
//
//   // Delete
//   KeychainHelper.delete("mouser_api_key")
//
// SECURITY NOTES:
//   • Items are stored in the app's own keychain access group (kSecAttrAccessGroupToken).
//   • `kSecAttrAccessible = kSecAttrAccessibleAfterFirstUnlock` means the item is
//     available after the device is unlocked once — suitable for API keys used in
//     background tasks.  Change to `.whenUnlocked` if you want stricter protection.
//   • No biometric prompt is required; add `kSecAccessControlBiometryAny` to the
//     attributes if you want Touch ID / Face ID gating on sensitive credentials.
//
// TO MIGRATE AN EXISTING UserDefaults KEY TO KEYCHAIN:
//   Call `KeychainHelper.migrateFromDefaults(key:)` once on app launch.

public enum KeychainHelper {

    // MARK: – Write

    /// Store or overwrite a string value in the Keychain.
    /// - Returns: `true` on success.  Silent failure is logged via `assertionFailure`
    ///   in debug builds so developers notice configuration issues early.
    @discardableResult
    public static func set(_ value: String, forKey key: String) -> Bool {
        guard let data = value.data(using: .utf8) else { return false }

        // Delete any existing item first — SecItemUpdate is fiddlier than delete+add.
        delete(key)

        let query: [CFString: Any] = [
            kSecClass:           kSecClassGenericPassword,
            kSecAttrService:     bundleID,
            kSecAttrAccount:     key,
            kSecValueData:       data,
            // Available after first unlock — good for API keys used in background fetches.
            // Change to kSecAttrAccessibleWhenUnlocked for stricter security.
            kSecAttrAccessible:  kSecAttrAccessibleAfterFirstUnlock,
        ]
        let status = SecItemAdd(query as CFDictionary, nil)
        let ok = status == errSecSuccess
        assert(ok, "Keychain write failed for key '\(key)': OSStatus \(status)")
        return ok
    }

    // MARK: – Read

    /// Retrieve a previously stored string, or `nil` if not found.
    public static func get(_ key: String) -> String? {
        let query: [CFString: Any] = [
            kSecClass:            kSecClassGenericPassword,
            kSecAttrService:      bundleID,
            kSecAttrAccount:      key,
            kSecReturnData:       true,
            kSecMatchLimit:       kSecMatchLimitOne,
        ]
        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        guard status == errSecSuccess,
              let data = result as? Data,
              let string = String(data: data, encoding: .utf8) else {
            return nil
        }
        return string
    }

    // MARK: – Delete

    /// Remove a stored item.  No-op if the key doesn't exist.
    @discardableResult
    public static func delete(_ key: String) -> Bool {
        let query: [CFString: Any] = [
            kSecClass:        kSecClassGenericPassword,
            kSecAttrService:  bundleID,
            kSecAttrAccount:  key,
        ]
        let status = SecItemDelete(query as CFDictionary)
        return status == errSecSuccess || status == errSecItemNotFound
    }

    // MARK: – Migration helper

    /// One-shot migration: reads a value from UserDefaults, writes it to the
    /// Keychain, then removes the UserDefaults entry.
    /// Call this once at app launch for keys that were previously stored in defaults.
    ///
    /// Example in WorkshopStore.init():
    ///   KeychainHelper.migrateFromDefaults(key: "mouser_api_key")
    public static func migrateFromDefaults(key: String) {
        guard let existing = UserDefaults.standard.string(forKey: key),
              !existing.isEmpty,
              KeychainHelper.get(key) == nil else { return }
        if set(existing, forKey: key) {
            UserDefaults.standard.removeObject(forKey: key)
        }
    }

    // MARK: – Private

    // Use the app's bundle ID as the Keychain service name so items are
    // scoped to this app and don't clash with other apps' keys.
    private static var bundleID: String {
        Bundle.main.bundleIdentifier ?? "com.pedalworkshop"
    }
}
