import { useEffect, useMemo, useState } from 'react'
import {
  browserLocalPersistence,
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  setPersistence,
  signInWithEmailAndPassword,
  signOut,
} from 'firebase/auth'

import { auth } from '../services/firebase.js'
import { AuthContext } from './authContext.js'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    let unsubscribe

    async function observeAuthState() {
      try {
        await setPersistence(auth, browserLocalPersistence)
      } catch {
        // Firebase's default browser persistence remains a safe fallback.
      }

      if (!active) return

      unsubscribe = onAuthStateChanged(auth, (currentUser) => {
        setUser(currentUser)
        setLoading(false)
      })
    }

    observeAuthState()

    return () => {
      active = false
      unsubscribe?.()
    }
  }, [])

  const value = useMemo(
    () => ({
      user,
      loading,
      register: (email, password) => createUserWithEmailAndPassword(auth, email, password),
      login: (email, password) => signInWithEmailAndPassword(auth, email, password),
      logout: () => signOut(auth),
      getIdToken: (forceRefresh = false) =>
        auth.currentUser ? auth.currentUser.getIdToken(forceRefresh) : Promise.resolve(null),
    }),
    [loading, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
