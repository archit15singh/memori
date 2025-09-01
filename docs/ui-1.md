create a UI for a reflective journaling bot. there is one screen which has a chatbot on the left side and a panel of memory objects as badges or tags on the right.

left side, 3/4th horizantally, there is a chat UI.
user types journal entry, presses enter, the backend API (stubbed) is called with the user entry, and we get an output after 2 seconds.

when the user presses enter, the user entry scrolls to the top of the chat container where the messages are shown, while waiting for the backend to respond. when the backend responds, the response is then rendered right below the user entry. this help better UX, since every user entry + submit should be seen in the chat messages panel on its own, with the user entry at the top, and response below it.

the right side, 1/4th horizontally, there is a memories panel. where we list the current memories, normal CRUD On these. on UI these are badges, fetch from backend do CRUD. skip backend calls and stub them to be replaced later easily.

only focus on the frontend. react.
